"""TOTP-setup — hver bruger sætter sin EGEN anden faktor.

Generér nøgle, gem på brugeren, returnér otpauth://-URI så desk kan vise QR.
Blokerende DB-arbejde via asyncio.to_thread (--workers 1 frys-fælde). Secret
returneres KUN ved setup (engangs-visning).

## Hvorfor ruten ikke længere er owner-only (målt 31/10-2026)

Den var owner-only, og det lukkede en hel kæde for alle andre. Uden en seed
kan `device_pairing.kraev_totp` ikke verificere noget — og uden det kan et
medlem ikke registrere sin egen enhed. Så snart enheds-reglen (`kraev_aktivt`)
blev tændt 30/10, blev code mode spærret for medlemmer med en besked der bad
dem gøre præcis det ruten nægtede dem: «Slå totrinsbekræftelse til først
(Indstillinger → Konto)». Målt: Mikkel (uid 238975101381378048) havde nul
enheder og fik 403 på `POST /chat/stream/v2`.

## Hvorfor det ikke flytter en grænse

Seed'en er per-bruger (`users.totp_seed`, krypteret per-bruger i `user_db`)
og bruges til to helt forskellige ting:

- **Brugerens EGEN enhed** — `kraev_totp(user_id, kode)` slår op på kalderens
  eget id. Det er denne rute der gør den vej mulig.
- **Ejerens override-bagdør** (`!override <kode>`, §6.3) — og DET opslag
  rammer udelukkende `get_owner().discord_id`, aldrig den kaldende:
  `discord_gateway.py:1390`, `telegram_gateway.py:360`,
  `chat_stream_v2.py:196`. En members seed kan derfor aldrig åbne ejerens
  override, uanset hvad den indeholder.

At sætte sin egen anden faktor er ikke en privilegeret handling. At sætte en
ANDENS ville være — og det kan ruten ikke: den skriver altid på
`current_user_id()`.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth/totp", tags=["auth"])


def _bruger_eller_403():
    """Returnér den indloggede bruger. Ubundet (no-auth) → owner.

    Kun en UKENDT bruger afvises: en identitet der ikke findes i `users.json`
    har ingen seed at skrive til, og et 403 er den ærlige besked om det.
    Rollen er uden betydning — se modulets docstring for hvorfor.
    """
    from core.identity.workspace_context import current_user_id
    from core.identity.users import find_user_by_discord_id, get_owner
    uid = current_user_id() or None
    if uid is None:
        return get_owner()  # ubundet = owner-kontekst
    u = find_user_by_discord_id(str(uid))
    if u is None:
        raise HTTPException(status_code=403, detail="ukendt bruger — kan ikke opsætte 2FA")
    return u


@router.get("/status")
async def totp_status() -> dict:
    bruger = await asyncio.to_thread(_bruger_eller_403)
    return {"configured": bool(bruger and bruger.totp_seed), "account": bruger.name if bruger else None}


def _do_setup() -> dict:
    bruger = _bruger_eller_403()
    if bruger is None:
        raise HTTPException(status_code=400, detail="ingen bruger registreret")
    from core.services.totp_verifier import generate_seed, provisioning_uri
    from core.identity.users import set_totp_seed
    seed = generate_seed()
    if not set_totp_seed(discord_id=bruger.discord_id, seed=seed):
        raise HTTPException(status_code=500, detail="kunne ikke gemme seed")
    return {
        "secret": seed,
        "provisioning_uri": provisioning_uri(seed, account=bruger.name, issuer="Jarvis"),
        "account": bruger.name,
    }


@router.post("/setup")
async def totp_setup() -> dict:
    """Generér + gem en ny TOTP-seed for den indloggede bruger. Returnér secret
    + otpauth-URI (engangs-visning til QR/scanning). Overskriver eksisterende
    seed (re-setup). Skriver ALTID på kalderen selv — aldrig på en anden."""
    return await asyncio.to_thread(_do_setup)


@router.post("/revoke")
async def totp_revoke() -> dict:
    """Fjern kalderens EGEN TOTP-seed (deaktivér til ny setup, §9 kompromittering)."""
    def _revoke() -> dict:
        bruger = _bruger_eller_403()
        if bruger is None:
            raise HTTPException(status_code=400, detail="ingen bruger")
        from core.identity.users import set_totp_seed
        set_totp_seed(discord_id=bruger.discord_id, seed="")
        return {"status": "ok", "configured": False}
    return await asyncio.to_thread(_revoke)
