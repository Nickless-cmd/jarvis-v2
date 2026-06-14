"""Pending UI-panel-kald (spec §8.2, Fase 6 #3).

Jarvis kan bede desk-appen om at åbne et panel (preview / højre side-panel / fil-træ)
når han vil vise noget. Han kan ikke selv manipulere klientens DOM, så han lægger en
pending forespørgsel her; desk-appen poller, åbner panelet og ack'er.

DB-backed (runtime_state_kv) — cross-proces (api↔runtime). Samme mønster som
share_guard_store. Owner i egen session: desk kan auto-åbne uden approval-kort (§8.2).
"""
from __future__ import annotations

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "ui_panel_requests"
_MAX = 50
_VALID_PANELS = ("preview", "right", "files")


def _load() -> list[dict]:
    raw = get_runtime_state_value(_KEY, [])
    return raw if isinstance(raw, list) else []


def _save(items: list[dict]) -> None:
    set_runtime_state_value(_KEY, items[-_MAX:])


def request_panel(*, request_id: str, panel: str, session_id: str, detail: str, created_at: str) -> dict:
    """Registrér en panel-åbnings-forespørgsel. panel clamps til kendte værdier."""
    p = panel if panel in _VALID_PANELS else "preview"
    rec = {
        "id": str(request_id),
        "panel": p,
        "session_id": str(session_id or ""),
        "detail": str(detail or "")[:200],
        "status": "pending",
        "created_at": str(created_at or ""),
    }
    items = [r for r in _load() if r.get("id") != rec["id"]]
    items.append(rec)
    _save(items)
    return rec


def list_pending() -> list[dict]:
    """Uafgjorte panel-forespørgsler (desk poller)."""
    return [r for r in _load() if r.get("status") == "pending"]


def ack(request_id: str) -> bool:
    """Markér en forespørgsel som åbnet (consumeret af desk)."""
    items = _load()
    found = False
    for r in items:
        if r.get("id") == str(request_id) and r.get("status") == "pending":
            r["status"] = "opened"
            found = True
    if found:
        _save(items)
    return found
