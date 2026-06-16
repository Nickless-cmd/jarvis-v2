"""Pending UI-panel-kald (spec §8.2, Fase 6 #3, opdateret 2026-06-16 med scope).

Jarvis kan bede desk-appen om at åbne et panel (preview / højre side-panel /
fil-træ) når han vil vise noget. Han kan ikke selv manipulere klientens DOM, så
han lægger en pending forespørgsel her; desk-appen poller, åbner panelet og ack'er.

DB-backed (runtime_state_kv) — cross-proces (api↔runtime). Samme mønster som
share_guard_store. Owner i egen session: desk kan auto-åbne uden approval-kort (§8.2).
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime import jarvis_db as _jarvis_db

_KEY = "ui_panel_requests"

VALID_PANELS = {"preview", "right", "files", "file_tree", "settings"}
VALID_SCOPES = {"repo", "workstation"}


def request_panel(
    panel: str,
    *,
    detail: str = "",
    scope: str = "repo",
    session_id: str = "",
) -> dict[str, Any]:
    """Tilføj en pending panel-forespørgsel.

    Returns dict med request-detaljer (inkl. id). Kaster ValueError ved ugyldig
    panel/scope.
    """
    panel = panel.strip().lower()
    scope = scope.strip().lower()

    if panel not in VALID_PANELS:
        raise ValueError(f"ukendt panel '{panel}' (gyldige: {', '.join(sorted(VALID_PANELS))})")
    if scope not in VALID_SCOPES:
        raise ValueError(f"ukendt scope '{scope}' (gyldige: {', '.join(sorted(VALID_SCOPES))})")

    req: dict[str, Any] = {
        "id": f"panel-{uuid4().hex[:12]}",
        "panel": panel,
        "scope": scope,
        "detail": detail,
        "session_id": session_id,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }

    state = _load()
    state.append(req)
    _save(state)
    return req


def list_pending(*, session_id: str = "") -> list[dict[str, Any]]:
    """Returnér alle pending requests (status='pending'), valgfrit filtreret på session.
    For owner-sessioner: returnér alle pending (ingen godkendelse nødvendig).
    """
    state = _load()
    if session_id:
        return [r for r in state if r["status"] == "pending" and r.get("session_id") == session_id]
    return [r for r in state if r["status"] == "pending"]


def ack_panel(request_id: str) -> bool:
    """Markér en request som 'opened' (desk-appen har åbnet panelet)."""
    state = _load()
    for r in state:
        if r["id"] == request_id:
            r["status"] = "opened"
            _save(state)
            return True
    return False


def _load() -> list[dict[str, Any]]:
    try:
        raw = _jarvis_db.get(_KEY, "{}")
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _save(state: list[dict[str, Any]]) -> None:
    # Hold kun de seneste 50 entries for at undgå at DB vokser
    trimmed = state[-50:]
    _jarvis_db.set(_KEY, json.dumps(trimmed, ensure_ascii=False))
