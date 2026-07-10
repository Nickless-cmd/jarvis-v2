"""State-flag tools (leak-kandidat #1, 2026-07-10).

set_flag / get_flag / clear_flag / list_flags — letvægts nøgle→værdi med TTL,
cross-session, pr. bruger. Strikst resultat-kontrakt: set_flag LÆSER TILBAGE og
bekræfter (tool-fidelity-læren) — et "ok" er bevis for at flaget faktisk står der.
"""
from __future__ import annotations

from typing import Any

from core.services.state_flag_store import (
    set_flag, get_flag, clear_flag, list_flags,
)


def _uid() -> str:
    try:
        from core.identity.workspace_context import current_user_id
        return current_user_id() or "default"
    except Exception:
        return "default"


def _exec_set_flag(args: dict[str, Any]) -> dict[str, Any]:
    key = str(args.get("key") or "").strip()
    if not key:
        return {"status": "error", "error": "key er påkrævet"}
    ttl = args.get("ttl_minutes")
    try:
        rec = set_flag(key, args.get("value"), ttl_minutes=(float(ttl) if ttl else None), user_id=_uid())
    except Exception as exc:
        return {"status": "error", "error": f"set_flag fejlede: {exc}"}
    # STRIKS BEKRÆFTELSE: læs tilbage — "ok" er bevis for at flaget står der.
    back = get_flag(key, user_id=_uid())
    if not back:
        return {"status": "error", "error": "flag ikke bekræftet efter skriv"}
    return {"status": "ok", "confirmed": True, "flag": back,
            "note": f"Flag '{key}' sat og bekræftet." + (f" Udløber {rec['expires_at']}." if rec.get("expires_at") else " Intet udløb.")}


def _exec_get_flag(args: dict[str, Any]) -> dict[str, Any]:
    key = str(args.get("key") or "").strip()
    if not key:
        return {"status": "error", "error": "key er påkrævet"}
    rec = get_flag(key, user_id=_uid())
    if rec is None:
        return {"status": "ok", "found": False, "key": key,
                "note": f"Intet aktivt flag '{key}' (ukendt eller udløbet)."}
    return {"status": "ok", "found": True, "flag": rec}


def _exec_clear_flag(args: dict[str, Any]) -> dict[str, Any]:
    key = str(args.get("key") or "").strip()
    if not key:
        return {"status": "error", "error": "key er påkrævet"}
    existed = clear_flag(key, user_id=_uid())
    # Bekræft: flaget er væk.
    gone = get_flag(key, user_id=_uid()) is None
    return {"status": "ok", "confirmed": gone, "existed": existed, "key": key,
            "note": (f"Flag '{key}' fjernet." if existed else f"Flag '{key}' fandtes ikke.")}


def _exec_list_flags(_args: dict[str, Any]) -> dict[str, Any]:
    flags = list_flags(user_id=_uid())
    return {"status": "ok", "count": len(flags), "flags": flags}


STATE_FLAG_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "set_flag",
        "description": ("Sæt et letvægts flag (nøgle→værdi) der overlever sessioner, evt. med TTL. "
                        "Brug til at huske noget til senere UDEN at fylde memory: 'afventer bruger-svar', "
                        "'denne output skal reviewes', 'husk at tjekke X om 30 min'. Sæt ttl_minutes for "
                        "auto-udløb. Bekræftes ved read-back (resultatet ER bevis for at flaget står der)."),
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Flag-nøgle (unik identifikator)"},
            "value": {"description": "Vilkårlig værdi (streng/tal/objekt)"},
            "ttl_minutes": {"type": "number", "description": "Valgfri auto-udløb i minutter (udelad = permanent til clear_flag)"},
        }, "required": ["key"]},
    }},
    {"type": "function", "function": {
        "name": "get_flag",
        "description": "Læs et flag sat med set_flag. Returnerer værdi + udløb, eller found=false hvis ukendt/udløbet.",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Flag-nøgle"},
        }, "required": ["key"]},
    }},
    {"type": "function", "function": {
        "name": "clear_flag",
        "description": "Fjern et flag. Bekræftes (confirmed=true når flaget er væk).",
        "parameters": {"type": "object", "properties": {
            "key": {"type": "string", "description": "Flag-nøgle"},
        }, "required": ["key"]},
    }},
    {"type": "function", "function": {
        "name": "list_flags",
        "description": "Se alle dine aktive (ikke-udløbne) flag.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]

STATE_FLAG_TOOL_HANDLERS: dict[str, Any] = {
    "set_flag": _exec_set_flag,
    "get_flag": _exec_get_flag,
    "clear_flag": _exec_clear_flag,
    "list_flags": _exec_list_flags,
}
