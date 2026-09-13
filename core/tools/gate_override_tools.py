"""Gate-override-værktøj — Jarvis' eksplicitte svar på en gate der tog fejl.

Se ``core/services/gate_override.py`` for mekanikken. Kort: gaten fyrer og logger
FØRST; dette værktøj armerer ÉN one-shot for præcis den hændelse, så Jarvis kan
gentage kaldet og komme igennem — synligt, med begrundelse, og med læring.

Tilføjet 13/9-2026 (Bjørn: "B med C som forudsætning" — autoritet inden for ansvar,
men kun eksplicit og logget).
"""
from __future__ import annotations

from typing import Any


def _exec_override_gate(args: dict[str, Any]) -> dict[str, Any]:
    event_id = str(args.get("event_id") or "").strip()
    reason = str(args.get("reason") or "").strip()
    ttl = args.get("ttl_seconds")
    try:
        from core.services.gate_override import arm_override
        return arm_override(
            event_id,
            reason,
            ttl_seconds=(float(ttl) if ttl is not None else None),
        )
    except Exception as exc:
        return {"status": "error", "error": f"override_gate fejlede: {exc}"}


def _exec_gate_override_status(_args: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.services.gate_override import override_state
        return override_state()
    except Exception as exc:
        return {"status": "error", "error": f"gate_override_status fejlede: {exc}"}


GATE_OVERRIDE_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "override_gate",
        "description": (
            "Armér ÉN one-shot overstyring af veto-gaten for præcis den hændelse du "
            "blev blokeret af. Brug den når gaten tog fejl: du har læst veto-beskeden, "
            "vurderet at blokeringen ikke er berettiget, og kan begrunde hvorfor. "
            "Gaten fyrer og logger FØRST — dette er et svar på signalet, ikke en vej "
            "udenom det. Armeringen gælder ÉT kald til dét værktøj, udløber ubrugt "
            "efter 10 min, og forsvinder ved genstart. Næste kald skal overstyres igen. "
            "SECURITY-gates kan aldrig overstyres (§11.3). Begrundelse er påkrævet — "
            "en overstyring uden grund er en tavs omgåelse."
        ),
        "parameters": {"type": "object", "properties": {
            "event_id": {"type": "string",
                         "description": "Hændelses-ID'et fra veto-beskeden (fx 'veto-a1b2c3d4e5f6')."},
            "reason": {"type": "string",
                       "description": "Hvorfor blokeringen ikke er berettiget. Skrives i ledger'en og sendes til Bjørn."},
            "ttl_seconds": {"type": "number",
                            "description": "Valgfri levetid i sekunder (max 840 = 14 min). Udelad = 600 (10 min)."},
        }, "required": ["event_id", "reason"]},
    }},
    {"type": "function", "function": {
        "name": "gate_override_status",
        "description": (
            "Se hvilke gate-overstyringer der er armeret lige nu, hvor længe de lever, "
            "og hvad loftet er. Read-only."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]

GATE_OVERRIDE_TOOL_HANDLERS: dict[str, Any] = {
    "override_gate": _exec_override_gate,
    "gate_override_status": _exec_gate_override_status,
}
