"""Central 'keys' route — The Keymaker (optjent/udløbende/godkendt autonomi, owner-view).

Bjørn+Claude (6. jul, tema #4): "I cannot make the key. I have to find it." Centralen GENERERER
nøgler når en dimension optjener dem (track-record over tærskel), men kan ikke selv bruge dem —
kun owner godkender. En godkendt nøgle flipper sit flag i en TTL og AUTO-reverterer. Én dør ad
gangen, ingen permanent privilege-crawl.

GET  /central/keys            → aktive/afventende/optjente nøgler (metadata-only).
POST /central/keys/{id}/approve → OWNER godkender en pending nøgle → flip flag ON i TTL.
Owner-gated, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/central", tags=["central-keys"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _require_owner_strict() -> None:
    """Fail-closed gate for privilege-eskalering (nøgle-godkendelse giver Jarvis mere autonomi)."""
    from apps.api.jarvis_api.routes.central_auth import require_central_owner_strict
    require_central_owner_strict()


@router.get("/keys")
def get_keys(include_expired: int = 0) -> dict:
    """Nøgle-oversigt: afventende (dit ja mangler) + åbne + optjente dimensioner. Owner-only."""
    _require_owner()
    try:
        from core.services.central_keymaker import build_keymaker_surface, list_keys
        surf = build_keymaker_surface()
        if include_expired:
            surf["keys"] = list_keys(include_expired=True)
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf


@router.post("/keys/{key_id}/approve")
def approve(key_id: int) -> dict:
    """OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL (auto-reverterer)."""
    _require_owner_strict()   # privilege-eskalering → fail-closed (kræver bekræftet owner-token)
    try:
        from core.services.central_keymaker import approve_key
        return approve_key(key_id)
    except Exception as exc:  # svarer med fejlen til ejeren; en godkendelse der kaster maa ikke give 500
        logger.warning("keymaker: godkendelse af noegle %s fejlede: %s", key_id, exc)
        return {"ok": False, "error": str(exc)[:120]}


@router.post("/keys/{key_id}/reject")
def reject(key_id: int, reason: str = "") -> dict:
    """OWNER-handling: luk en pending nøgle uden at godkende den.

    Uden denne vej kan en forældet nøgle aldrig lukkes, og `_mind_om_ventende` bliver ved at
    minde om den. Kræver ikke strict-gate: at afvise en eskalering er ikke en eskalering.
    """
    _require_owner()
    try:
        from core.services.central_keymaker import reject_key
        return reject_key(key_id, reason=reason)
    except Exception as exc:  # svarer med fejlen til ejeren; en afvisning der kaster maa ikke give 500
        logger.warning("keymaker: afvisning af noegle %s fejlede: %s", key_id, exc)
        return {"ok": False, "error": str(exc)[:120]}
