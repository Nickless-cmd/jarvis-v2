"""Visnings-forespørgsler: Jarvis spørger desk, desk SVARER.

Claude Desktops `view-request`-protokol (Jarvis' kortlægning
cc-desktop-styring-indefra.md, bekræftet 19/9-2026 mod MCP-serveren `ccd_view`
som Claude Code selv har): tre operationer — `get_layout`, `show_pane`,
`close_pane` — korreleret på et request-id. Den der spørger, VENTER på svaret;
det er ikke fire-and-forget.

Det er forskellen fra `ui_panel_store`, som kun kan kvittere «åbnet». Her
bærer svaret indhold: hvad står på skærmen, hvilke paneler er åbne, og — når
noget ikke kan lade sig gøre — en fejltekst der siger HVAD der mangler
(«Terminalen findes kun i kode-tilstand»), som CC's.

DB-backed i `runtime_state_kv` — værktøjet kører i runtime-processen, desk
taler med api-processen. Samme mønster som `ui_panel_store`.
"""
from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value

__all__ = ["opret", "ventende", "svar", "hent", "vent_paa_svar", "OPERATIONER"]

_NOEGLE = "view_requests"
OPERATIONER = frozenset({"get_layout", "show_pane", "close_pane"})
#: En forespørgsel ingen har svaret på efter så længe, er forældet — desk
#: skal ikke udføre et «vis diff» Jarvis for længst har opgivet.
FORAELDET_S = 30.0


def _laes() -> list[dict[str, Any]]:
    try:
        data = json.loads(get_runtime_state_value(_NOEGLE) or "[]")
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _gem(tilstand: list[dict[str, Any]]) -> None:
    set_runtime_state_value(_NOEGLE, json.dumps(tilstand[-50:], ensure_ascii=False))


def opret(op: str, args: dict[str, Any] | None, *, session_id: str) -> dict[str, Any]:
    if op not in OPERATIONER:
        raise ValueError(f"ukendt operation {op!r}")
    req = {
        "id": f"view-{uuid4().hex[:12]}",
        "op": op,
        "args": dict(args or {}),
        "session_id": session_id,
        "status": "pending",
        "oprettet": time.time(),
        "created_at": datetime.now(UTC).isoformat(),
    }
    t = _laes()
    t.append(req)
    _gem(t)
    return req


def ventende() -> list[dict[str, Any]]:
    """Ubesvarede, ikke-forældede forespørgsler."""
    nu = time.time()
    return [r for r in _laes()
            if r.get("status") == "pending" and nu - float(r.get("oprettet") or 0) < FORAELDET_S]


def hent(request_id: str) -> dict[str, Any] | None:
    for r in _laes():
        if r.get("id") == request_id:
            return r
    return None


def svar(request_id: str, resultat: dict[str, Any]) -> bool:
    """Desk svarer. Kun én gang: et andet vindue må ikke overskrive svaret."""
    t = _laes()
    for r in t:
        if r.get("id") == request_id:
            if r.get("status") != "pending":
                return False
            r["status"] = "svaret"
            r["resultat"] = resultat
            _gem(t)
            return True
    return False


def vent_paa_svar(request_id: str, *, frist_s: float, interval_s: float = 0.2) -> dict[str, Any] | None:
    slut = time.monotonic() + frist_s
    while time.monotonic() < slut:
        r = hent(request_id)
        if r and r.get("status") == "svaret":
            return dict(r.get("resultat") or {})
        time.sleep(interval_s)
    return None
