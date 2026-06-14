"""Pending cross-user share-beslutninger — DB-backed kø (spec §4.4, Fase 6 #1).

Når cross_user_share_guard flagger et udgående svar (Jarvis nævnte en anden bruger),
registreres en pending beslutning her i stedet for at blive jammet ind i den live
token-stream (som ville konflikte med streaming). Beslutningen dukker op som et kort
i Cowork-approval-køen: owner svarer "okay at dele" eller "hold privat".

DB-backed (runtime_state_kv) — cross-proces (api↔runtime), samme mønster som
override_store. Append-only liste under én nøgle; små mængder (kun ved faktiske hits).
"""
from __future__ import annotations

from core.runtime.db import get_runtime_state_value, set_runtime_state_value

_KEY = "cross_user_share_pending"
_MAX = 200  # backstop mod ubundet vækst


def _load() -> list[dict]:
    raw = get_runtime_state_value(_KEY, [])
    return raw if isinstance(raw, list) else []


def _save(items: list[dict]) -> None:
    set_runtime_state_value(_KEY, items[-_MAX:])


def record_pending(
    *,
    decision_id: str,
    session_id: str,
    current_user_id: str,
    mentioned_users: list[str],
    text_preview: str,
    created_at: str,
) -> dict:
    """Registrér en pending share-beslutning. Returnér recorden."""
    rec = {
        "id": str(decision_id),
        "session_id": str(session_id or ""),
        "current_user_id": str(current_user_id or ""),
        "mentioned_users": list(mentioned_users or []),
        "text_preview": str(text_preview or "")[:240],
        "status": "pending",
        "created_at": str(created_at or ""),
    }
    items = [r for r in _load() if r.get("id") != rec["id"]]
    items.append(rec)
    _save(items)
    return rec


def list_pending() -> list[dict]:
    """Alle uafgjorte share-beslutninger (til Cowork-køen)."""
    return [r for r in _load() if r.get("status") == "pending"]


def resolve(decision_id: str, *, shared: bool) -> bool:
    """Afgør en beslutning: shared=True (okay at dele) / False (hold privat).

    Returnerer True hvis fundet + opdateret.
    """
    items = _load()
    found = False
    for r in items:
        if r.get("id") == str(decision_id) and r.get("status") == "pending":
            r["status"] = "shared" if shared else "kept_private"
            found = True
    if found:
        _save(items)
    return found
