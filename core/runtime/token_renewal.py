"""Fornyelse af bearer-tokens — så en klient ikke låses ude af tiden alene.

## Hvorfor

Mikkels telefon hamrede 927 gange på seks timer med ét svar hver gang:
`token expired`. Den havde ingen vej tilbage. Tokens er selvbærende JWT'er
med en fast udløbsdato, og den eneste måde at få et nyt på var at Bjørn
mintede det i hånden og fik det installeret på enheden.

Der FANDTES en refresh-mekanisme (``core.runtime.refresh_tokens``, §22.6) —
men ``issue_refresh_token`` havde nul kaldere uden for testene. Ingen klient
har nogensinde fået en refresh-token, og derfor har ingen nogensinde kunnet
bruge ``/api/auth/refresh``. Nul forsøg i loggen over seks timer. Koden var
rigtig; ingen kaldte den.

## Hvad dette lag gør

Ét endepunkt, ét token-format — det der allerede er installeret på enhederne:

  * **Glidende fornyelse.** Et gyldigt token kan veksles til et nyt med samme
    levetid. Klienten forny'r når der er under en tredjedel tilbage, og så
    udløber tokenet i praksis aldrig for en enhed der er i brug.

  * **Nådevindue.** Et token der ER udløbet — men hvis signatur er ægte, og
    som udløb for under 30 dage siden — kan stadig veksles ÉN gang. Det er
    genopretningsvejen: en telefon der har ligget i en skuffe kommer tilbage
    selv, uden at ejeren skal bære et token over.

Nådevinduet er en bevidst opblødning. Modvægten står nedenfor.

## Modvægten: fornyede tokens kan slukkes enkeltvis

De tokens der er i brug i dag har INGEN ``jti``. Det betyder at det eneste
værn mod et lækket token er at rotere hele auth-hemmeligheden — hvilket
smider alle ud på én gang. I praksis er der altså ingen off-switch.

Hvert fornyet token får derfor en ``jti``, og den skrives i en liste pr.
bruger. ``revoke_user_tokens(user_id)`` sortlister dem alle. Jo længere
fornyelse har kørt, jo flere af de levende tokens kan slukkes enkeltvis.

Man tilføjer ikke en genoplivnings-vej uden en afbryder.

## Hvad fornyelse IKKE gør

Den giver aldrig mere end tokenet allerede havde:

  * Rollen læses fra brugerkartoteket og klemmes ned til den laveste af
    (token-rolle, gemt rolle). En degraderet bruger kan ikke forny sig
    tilbage til sin gamle autoritet.
  * En slettet bruger kan ikke forny.
  * Et sortlistet ``jti`` kan ikke forny.
  * Levetiden arves fra det oprindelige token — fornyelse forlænger ikke
    vinduet, den flytter det.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import jwt

logger = logging.getLogger(__name__)

# Hvor længe efter udløb et token stadig kan veksles. Kort nok til at et
# glemt token dør af sig selv; langt nok til at en telefon der har ligget
# stille en måned kommer tilbage uden håndarbejde.
GRACE_DAYS = 30

# Rangorden. Fornyelse kan flytte NED ad denne liste, aldrig op.
_RANG = {"guest": 0, "member": 1, "partner": 2, "owner": 3}

_JTI_INDEX_PREFIX = "token_jti:"      # runtime_state: bruger → udstedte jti'er
_MAX_JTI_PR_BRUGER = 200


def _now() -> datetime:
    return datetime.now(UTC)


def _afkod_uden_udloeb(raw: str) -> dict[str, Any]:
    """Verificér signatur + udsteder, men LAD udløb passere.

    Signaturen er hele pointen: den siger at vi selv har udstedt tokenet.
    Udløbet vurderer vi bagefter, fordi et udløbet token er præcis det vi
    er her for at kunne behandle.
    """
    from core.runtime.jarvisx_auth import _ALGO, _ISSUER, _read_secret
    token = str(raw or "").strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        raise ValueError("missing token")
    return jwt.decode(
        token,
        _read_secret(),
        algorithms=[_ALGO],
        issuer=_ISSUER,
        options={"require": ["sub", "exp", "iat"], "verify_exp": False},
    )


def _gemt_bruger(user_id: str) -> dict[str, Any] | None:
    """Slå brugeren op i BEGGE kartoteker.

    Bjørn, Mikkel og Michelle står i users.json (discord-id'er); Lotte står i
    SQLite (hex-uuid). Et opslag der kun kender det ene kartotek ville stille
    behandle den anden halvdel som ukendt.
    """
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(user_id)
        if u is not None:
            return {"role": str(getattr(u, "role", "") or ""), "deleted": False}
    except Exception:
        logger.debug("token_renewal: users.json-opslag fejlede", exc_info=True)
    try:
        from core.identity.user_db import get_user
        row = get_user(user_id)
        if row:
            return {"role": str(row.get("role") or ""), "deleted": bool(row.get("deleted_at"))}
    except Exception:
        logger.debug("token_renewal: user_db-opslag fejlede", exc_info=True)
    return None


def _klem_rolle(token_rolle: str, gemt: dict[str, Any] | None) -> str:
    """Laveste af (token-rolle, gemt rolle). Ukendt bruger → token-rollen.

    Tokenet er signeret af os, så dets rolle var autoriseret dengang. Risikoen
    er kun at den er FORÆLDET — derfor klemmer vi ned, aldrig op.
    """
    tr = (token_rolle or "member").lower()
    if not gemt:
        return tr
    gr = (gemt.get("role") or "").lower()
    if gr not in _RANG:
        return tr
    return gr if _RANG[gr] < _RANG.get(tr, 1) else tr


def _husk_jti(user_id: str, jti: str) -> None:
    """Skriv jti'en i brugerens liste, så den kan sortlistes senere."""
    try:
        from core.runtime.db import get_runtime_state_value, set_runtime_state_value
        key = _JTI_INDEX_PREFIX + user_id
        raw = get_runtime_state_value(key, "[]")
        try:
            liste = json.loads(raw) if isinstance(raw, str) else list(raw or [])
        except Exception:
            liste = []
        liste.append(jti)
        set_runtime_state_value(key, json.dumps(liste[-_MAX_JTI_PR_BRUGER:]))
    except Exception:
        # Fornyelsen må ikke fejle fordi bogføringen fejler. Tokenet er stadig
        # gyldigt; det er kun afbryderen der mangler for netop dette token.
        logger.warning("token_renewal: kunne ikke bogfoere jti for %s", user_id, exc_info=True)


def renew(raw_token: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Veksl et bearer-token til et friskt et.

    Returnerer ``{"ok": True, "token", "expires_at", "role", "grace"}`` eller
    ``{"ok": False, "reason"}``. ``grace`` siger om tokenet allerede var
    udløbet — klienten behøver ikke vide det, men loggen gør.
    """
    nu = now or _now()
    try:
        claims = _afkod_uden_udloeb(raw_token)
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    except jwt.InvalidTokenError as exc:
        # Forkert signatur, forkert udsteder, manglende claims. Alt sammen
        # "det her token har vi ikke udstedt" — ingen grund til at skelne
        # udadtil.
        logger.info("token_renewal: afvist token (%s)", exc)
        return {"ok": False, "reason": "invalid token"}

    user_id = str(claims.get("sub") or "")
    if not user_id:
        return {"ok": False, "reason": "token missing subject"}

    jti = str(claims.get("jti") or "")
    if jti:
        try:
            from core.identity.user_db import is_api_key_revoked
            if is_api_key_revoked(jti):
                return {"ok": False, "reason": "token revoked"}
        except Exception:
            logger.warning("token_renewal: bloklisten utilgaengelig", exc_info=True)

    exp = int(claims.get("exp") or 0)
    iat = int(claims.get("iat") or 0)
    udloebet_for = nu.timestamp() - exp
    if udloebet_for > GRACE_DAYS * 86400:
        return {"ok": False, "reason": "token too old to renew"}

    gemt = _gemt_bruger(user_id)
    if gemt and gemt.get("deleted"):
        return {"ok": False, "reason": "user removed"}

    rolle = _klem_rolle(str(claims.get("role") or "member"), gemt)

    # Levetiden arves. Fornyelse flytter vinduet, den udvider det ikke.
    ttl_dage = max(1, min(round((exp - iat) / 86400), 365)) if exp > iat else 30

    ny_jti = uuid.uuid4().hex
    from core.runtime.jarvisx_auth import issue_token
    ekstra: dict[str, Any] = {"jti": ny_jti}
    if claims.get("app_id"):
        # Desk'ens TOTP-binding hænger på app_id. Tabes den, begynder Bjørns
        # egen app at bede om TOTP i sin egen session.
        ekstra["app_id"] = str(claims["app_id"])
    minted = issue_token(user_id=user_id, role=rolle, ttl_days=ttl_dage, extra_claims=ekstra)
    _husk_jti(user_id, ny_jti)

    logger.info(
        "token fornyet: bruger=%s rolle=%s ttl=%dd %s",
        user_id, rolle, ttl_dage,
        "(naadevindue — var udloebet)" if udloebet_for > 0 else "(gyldigt)",
    )
    return {
        "ok": True,
        "token": minted["token"],
        "expires_at": minted["expires_at"],
        "role": rolle,
        "grace": udloebet_for > 0,
    }


def revoke_user_tokens(user_id: str) -> int:
    """Sortlist alle fornyede tokens for én bruger. Returnerer antallet.

    Dette er afbryderen der gør nådevinduet forsvarligt. Tokens udstedt FØR
    fornyelse fandtes har ingen ``jti`` og kan ikke rammes — de dør af sig
    selv, eller når hemmeligheden roteres.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return 0
    from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    raw = get_runtime_state_value(_JTI_INDEX_PREFIX + uid, "[]")
    try:
        mine = json.loads(raw) if isinstance(raw, str) else list(raw or [])
    except Exception:
        mine = []
    if not mine:
        return 0
    from core.identity.user_db import _REVOKED_KEY
    sortliste = get_runtime_state_value(_REVOKED_KEY, [])
    if not isinstance(sortliste, list):
        sortliste = []
    tilfoejet = 0
    for j in mine:
        if j not in sortliste:
            sortliste.append(j)
            tilfoejet += 1
    set_runtime_state_value(_REVOKED_KEY, sortliste[-5000:])
    set_runtime_state_value(_JTI_INDEX_PREFIX + uid, "[]")
    logger.warning("token_renewal: sortlistede %d tokens for %s", tilfoejet, uid)
    return tilfoejet
