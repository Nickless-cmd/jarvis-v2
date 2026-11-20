"""Én rolle, tre kilder — og ét sted der skriver til dem alle.

MÅLT 20/11-2026: et rolleskift i `users.json` ændrede ikke den rolle
Google-login udstedte. En brugers rolle ligger i TRE lag, og kun det første
blev opdateret:

1. ``~/.jarvis-v2/config/users.json`` — Discord-identiteten. Bruges af
   ``allowed_tools``, ``find_user_by_discord_id`` og ``get_owner``.
2. ``users``-tabellen i ``jarvis.db`` — email/password-konti.
   ``/auth/login`` udsteder token med rollen herfra.
3. ``google_login_links`` — rollen der udstedes ved **Google-login**. For en
   bruger uden password er dette den ENESTE vej ind, så et skift der ikke
   rammer den er virkningsløst.

Konsekvensen af at ramme kun lag 1 blev målt samme dag: Michelle kørte videre
som ``member`` med 31 værktøjer i stedet for alle 527, fordi hendes login
læste lag 3. Fejlen så samtidig ud som noget andet — hendes session var
krypteret med hendes egen nøgle fra dengang hun var ``partner``, og da hun
midlertidigt blev ``owner`` kunne ``chat_crypto`` ikke længere resolvere
ejeren, så hvert svar blev en 500 som klienten viste som «Forbindelse
afbrudt». Et halvt rolleskift kan altså brække chat-krypteringen.

Den halve vej fandtes også i API'et: ``PATCH /users/{id}`` skrev rollen med
``update_user_row`` — kun lag 2. Ruten kalder nu denne funktion i stedet.

Derfor findes denne funktion: ét kald, alle tre kilder, og et svar der siger
hvad der faktisk skete i hver af dem.
"""
from __future__ import annotations

import logging
from typing import Any

from core.identity.household import VALID_ROLES

logger = logging.getLogger(__name__)

# Aktive tokens bærer rollen fra login-øjeblikket (`issue_token(role=…)`).
# Der findes ingen cache at invalidere — filen læses ved hvert kald — men en
# åben session kører videre med den gamle rolle indtil den fornyer.
_FORNYELSE_BEMAERK = "aktive session-tokens bærer den gamle rolle indtil fornyelse"


def set_role(
    *,
    role: str,
    discord_id: str = "",
    user_id: str = "",
    actor: str = "",
) -> dict[str, Any]:
    """Sæt en brugers rolle i alle tre kilder.

    Brugeren identificeres med ``discord_id`` ELLER ``user_id`` (den kanoniske
    UUID). Den anden form slås op, fordi de tre lag ikke deler nøgle: filen og
    Google-linkene kender Discord-id'et, mens ``users``-tabellen kender UUID'en
    — og link-tabellen kan bære begge.

    Returnerer hvad der faktisk skete pr. kilde — ikke blot «ok». En kilde der
    ikke blev ramt (fx en bruger der kun findes i ``users.json``) rapporteres
    som det, så et halvt skift aldrig kan ligne et helt.

    ``actor`` logges, så et rolleskift kan spores til hvem der bad om det.
    """
    role_c = str(role or "").strip().lower()
    if role_c not in VALID_ROLES:
        return {
            "ok": False,
            "error": f"ukendt rolle {role!r}",
            "gyldige": sorted(VALID_ROLES),
        }

    did = str(discord_id or "").strip()
    uid = str(user_id or "").strip()
    if not did and not uid:
        return {"ok": False, "error": "discord_id eller user_id mangler"}

    # ── Slå den anden id-form op, så alle tre lag kan rammes ─────────────
    konto: dict[str, Any] | None = None
    opslags_fejl = ""
    try:
        from core.identity.user_db import find_user_by_discord_id as _find_db_user
        from core.identity.user_db import get_user as _get_db_user

        konto = _get_db_user(uid) if uid else _find_db_user(did)
    except Exception as exc:  # fx AmbiguousRoutineIdentity — skal ses, ikke skjules
        opslags_fejl = str(exc)

    if konto:
        if not uid and konto.get("user_id"):
            uid = str(konto["user_id"])
        if not did and konto.get("discord_id"):
            did = str(konto["discord_id"])

    kilder: dict[str, Any] = {}
    fejl: list[str] = []
    if opslags_fejl:
        kilder["users_tabel"] = f"opslag fejlede: {opslags_fejl}"
        fejl.append(f"users_tabel opslag: {opslags_fejl}")

    # ── 1. users.json — Discord-identiteten ──────────────────────────────
    from core.identity import users as _users

    if not did:
        kilder["users_json"] = "ingen discord_id"
    elif _users.find_user_by_discord_id(did) is None:
        kilder["users_json"] = "findes ikke"
    else:
        try:
            kilder["users_json"] = _users.set_role(discord_id=did, role=role_c)
        except Exception as exc:  # rapporteres, sluges ikke
            kilder["users_json"] = f"fejl: {exc}"
            fejl.append(f"users_json: {exc}")

    # ── 2. users-tabellen — email/password-login ─────────────────────────
    if uid:
        try:
            from core.runtime import db_users as _dbu

            kilder["users_tabel"] = _dbu.update_user_row(uid, {"role": role_c})
        except Exception as exc:
            kilder["users_tabel"] = f"fejl: {exc}"
            fejl.append(f"users_tabel: {exc}")
    elif "users_tabel" not in kilder:
        kilder["users_tabel"] = "findes ikke"

    # ── 3. google_login_links — den vej Google-login udsteder token ──────
    # Begge id-former sendes: rækkerne er ikke normaliseret i den levende base.
    ids = [i for i in (did, uid) if i]
    try:
        from core.runtime import db_users as _dbu

        kilder["google_login_links"] = _dbu.update_google_link_role(ids, role_c)
    except Exception as exc:
        kilder["google_login_links"] = f"fejl: {exc}"
        fejl.append(f"google_login_links: {exc}")

    # ── Dom: blev NOGEN kilde faktisk ramt? ──────────────────────────────
    ramt = (
        kilder.get("users_json") is True
        or kilder.get("users_tabel") is True
        or (isinstance(kilder.get("google_login_links"), int)
            and kilder["google_login_links"] > 0)
    )
    if not ramt:
        return {
            "ok": False,
            "error": "ukendt bruger — ingen kilde havde noget at opdatere",
            "discord_id": did,
            "user_id": uid,
            "role": role_c,
            "kilder": kilder,
        }

    logger.info(
        "role_sync: %s → %s (actor=%s) kilder=%s",
        did or uid, role_c, actor or "ukendt", kilder,
    )

    ud: dict[str, Any] = {
        "ok": not fejl,
        "discord_id": did,
        "user_id": uid,
        "role": role_c,
        "kilder": kilder,
        "bemaerk": _FORNYELSE_BEMAERK,
    }
    if fejl:
        ud["fejl"] = fejl
    return ud
