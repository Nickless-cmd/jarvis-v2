"""Governed kill-switch for struktureret content-persist + wire. Default ON.

Flip OFF (owner) → nye beskeder persisteres som ren tekst igen og tool_result
streames som system_event igen. Allerede-skrevne content_json-rækker forbliver
læsbare uanset (adapteren i get_chat_session honorerer dem).
"""
from __future__ import annotations

_STATE_KEY = "structured_content_v2"


def _read_flag() -> object | None:
    """Læs rå flag-værdi fra runtime-state. None = usat."""
    from core.runtime.db import get_runtime_state_value
    return get_runtime_state_value(_STATE_KEY)


def structured_content_v2_enabled() -> bool:
    """True medmindre eksplicit slået fra ('off'/'0'/'false'/'no'). Læse-fejl → True
    (default ON er ejerens valg; kill-switch kræver et EKSPLICIT off for at slå fra)."""
    try:
        raw = _read_flag()
    except Exception:
        return True
    if raw is None:
        return True
    return str(raw).strip().lower() not in {"off", "0", "false", "no"}
