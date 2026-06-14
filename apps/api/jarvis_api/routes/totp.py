"""TOTP-setup for owner-override (spec §6.2). Armerer bagdøren: generér nøgle,
gem på owner, returnér otpauth://-URI så desk kan vise QR til scanning.

KUN owner i egen session må sætte/rotere sin egen seed (§6.0: seed er kun
owner-revokérbar, aldrig af Jarvis). Blokerende DB-arbejde via asyncio.to_thread
(--workers 1 frys-fælde). Secret returneres KUN ved setup (engangs-visning)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth/totp", tags=["auth"])


def _owner_or_403():
    """Returnér owner-User eller rejs 403. Ubundet (no-auth) → owner."""
    from core.identity.workspace_context import current_user_id
    from core.identity.users import find_user_by_discord_id, get_owner
    uid = current_user_id() or None
    if uid is None:
        return get_owner()  # ubundet = owner-kontekst
    u = find_user_by_discord_id(str(uid))
    if u is None or u.role != "owner":
        raise HTTPException(status_code=403, detail="kun owner kan opsætte 2FA")
    return u


@router.get("/status")
async def totp_status() -> dict:
    owner = await asyncio.to_thread(_owner_or_403)
    return {"configured": bool(owner and owner.totp_seed), "account": owner.name if owner else None}


def _do_setup() -> dict:
    owner = _owner_or_403()
    if owner is None:
        raise HTTPException(status_code=400, detail="ingen owner registreret")
    from core.services.totp_verifier import generate_seed, provisioning_uri
    from core.identity.users import set_totp_seed
    seed = generate_seed()
    if not set_totp_seed(discord_id=owner.discord_id, seed=seed):
        raise HTTPException(status_code=500, detail="kunne ikke gemme seed")
    return {
        "secret": seed,
        "provisioning_uri": provisioning_uri(seed, account=owner.name, issuer="Jarvis"),
        "account": owner.name,
    }


@router.post("/setup")
async def totp_setup() -> dict:
    """Generér + gem en ny TOTP-seed for owner. Returnér secret + otpauth-URI
    (engangs-visning til QR/scanning). Overskriver eksisterende seed (re-setup)."""
    return await asyncio.to_thread(_do_setup)


@router.post("/revoke")
async def totp_revoke() -> dict:
    """Fjern owners TOTP-seed (deaktivér override til ny setup, §9 kompromittering)."""
    def _revoke() -> dict:
        owner = _owner_or_403()
        if owner is None:
            raise HTTPException(status_code=400, detail="ingen owner")
        from core.identity.users import set_totp_seed
        set_totp_seed(discord_id=owner.discord_id, seed="")
        return {"status": "ok", "configured": False}
    return await asyncio.to_thread(_revoke)
