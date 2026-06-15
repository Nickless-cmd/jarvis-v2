"""Bygger data-payloaden for et tool-kald til jarvis-desk-chip'en (spec 2026-06-15).

Ren funktion: beriger et tool-resultat med (trunkerede) arguments + result_text, så
desk-appen kan vise hvad tool'et gjorde. Ingen præsentation (labels/ikoner bor i
frontendens toolRegistry). Interne args-nøgler (session_id, _runtime_*) fjernes.
"""
from __future__ import annotations

from typing import Any

_INTERNAL_ARG_KEYS = {"session_id"}


def build_tool_capability_payload(
    *,
    tool: str,
    status: str,
    arguments: Any = None,
    result_text: str = "",
    arg_value_cap: int = 600,
    result_cap: int = 4000,
) -> dict[str, Any]:
    args_out: dict[str, Any] = {}
    if isinstance(arguments, dict):
        for k, v in arguments.items():
            ks = str(k)
            if ks.startswith("_") or ks in _INTERNAL_ARG_KEYS:
                continue
            if isinstance(v, str) and len(v) > arg_value_cap:
                args_out[ks] = v[:arg_value_cap] + "…"
            else:
                args_out[ks] = v
    rt = str(result_text or "")
    if len(rt) > result_cap:
        rt = rt[:result_cap] + "\n…(trunkeret)"
    return {
        "type": "tool_result",
        "tool": str(tool),
        "status": str(status),
        "arguments": args_out,
        "result_text": rt,
    }
