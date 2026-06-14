"""Pending runtime→app instruktioner (spec §18.5, Fase 2).

Når runtime vil have appen til at handle på brugerens enhed (send besked via en
kanal, vis en notifikation, send en rapport), lægger den en struktureret
instruktion her. jarvis-desk poller, udfører via sit kanal-plugin / native
notifikation, og ack'er. Samme DB-backede mønster som [[ui_panel_store]] —
cross-proces (api↔runtime), så den virker uanset hvilken proces der dispatcher.

Validerer action mod cowork_dispatch's hvidliste, så kun kendte handlinger når
appen. Rører IKKE den live server-side Discord-gateway (additiv kanal).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.services.cowork_dispatch import build_app_instruction

_KEY = "app_dispatch_queue"
_MAX = 100


def _load() -> list[dict]:
    raw = get_runtime_state_value(_KEY, [])
    return raw if isinstance(raw, list) else []


def _save(items: list[dict]) -> None:
    set_runtime_state_value(_KEY, items[-_MAX:])


def enqueue(instruction: dict) -> dict | None:
    """Validér + kø en app-instruktion. Returnerer record (med id/created_at) eller
    None hvis instruktionen er ugyldig (ukendt action / manglende target_user)."""
    try:
        instr = build_app_instruction(
            action=str(instruction.get("action", "")),
            target_user=str(instruction.get("target_user", "")),
            channel=instruction.get("channel"),
            payload=instruction.get("payload"),
            requester=str(instruction.get("requester", "")),
        )
    except (ValueError, AttributeError):
        return None
    rec = {
        "id": uuid.uuid4().hex,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **instr,
    }
    items = _load()
    items.append(rec)
    _save(items)
    return rec


def list_pending() -> list[dict]:
    """Uafgjorte instruktioner i kø-rækkefølge (desk poller)."""
    return [r for r in _load() if r.get("status") == "pending"]


def ack(dispatch_id: str) -> bool:
    """Markér en instruktion som udført (consumeret af desk)."""
    items = _load()
    found = False
    for r in items:
        if r.get("id") == str(dispatch_id) and r.get("status") == "pending":
            r["status"] = "done"
            found = True
    if found:
        _save(items)
    return found
