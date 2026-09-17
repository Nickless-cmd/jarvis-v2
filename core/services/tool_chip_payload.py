"""Bygger data-payloaden for et tool-kald til jarvis-desk-chip'en (spec 2026-06-15).

Ren funktion: beriger et tool-resultat med (trunkerede) arguments + result_text, så
desk-appen kan vise hvad tool'et gjorde. Ingen præsentation (labels/ikoner bor i
frontendens toolRegistry). Interne args-nøgler (session_id, _runtime_*) fjernes.
"""
from __future__ import annotations

from typing import Any

_INTERNAL_ARG_KEYS = {"session_id"}


def trim_arguments(arguments: Any = None, *, arg_value_cap: int = 600) -> dict[str, Any]:
    """Argumenter uden interne nøgler og uden tekstvægge.

    Egen funktion siden 17/9-2026: linjen der vises når kaldet STARTER sender
    de samme argumenter som resultatet gør, og to steder der klipper hver sin
    måde ville få linjen til at skifte indhold når resultatet landede.
    """
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
    return args_out


def build_tool_capability_payload(
    *,
    tool: str,
    status: str,
    arguments: Any = None,
    result_text: str = "",
    arg_value_cap: int = 600,
    result_cap: int = 4000,
    call_id: str = "",
) -> dict[str, Any]:
    args_out = trim_arguments(arguments, arg_value_cap=arg_value_cap)
    rt = str(result_text or "")
    if len(rt) > result_cap:
        rt = rt[:result_cap] + "\n…(trunkeret)"
    ud: dict[str, Any] = {
        "type": "tool_result",
        "tool": str(tool),
        "status": str(status),
        "arguments": args_out,
        "result_text": rt,
    }
    # Modellens eget kald-id. Uden det faldt oversætteren tilbage på
    # VÆRKTØJSNAVNET som id, så to kald til samme værktøj i samme runde delte
    # identitet — og den linje der blev vist da kaldet startede, kunne ikke
    # finde sit eget resultat.
    if call_id:
        ud["capability_id"] = str(call_id)
    return ud
