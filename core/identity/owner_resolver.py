"""Owner-identity resolution for autonomous dispatch.

Threat model: Jarvis runs autonomous side-effects (wakeups, scheduled
reminders, heartbeat pings, proactive outreach) that can route through
chat sessions or Discord DMs. If those dispatches land in a non-owner's
session — typically a member like Mikkel who had a recent DM — the
member sees Jarvis spontaneously asking *Bjørn's* questions. That's a
privacy leak and a UX bug.

Root cause was bigger than any single dispatcher: the `pin_session`
helper in notification_bridge tracks "the most recently active session"
globally without distinguishing whose. So when Mikkel sends a DM,
his session gets pinned; the next autonomous wakeup or reminder fired
for Bjørn picks up the pin and dumps the message into Mikkel's chat.

This module centralises:
  * get_owner_discord_id()       — resolve the owner's Discord ID via
                                   discord_config and users.json
  * resolve_owner_target_session() — pick the right session for an
                                   autonomous Bjørn-event, never
                                   matching a non-owner session

Use this at every autonomous-dispatch site instead of calling
list_chat_sessions() / get_pinned_session_id() directly.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_owner_discord_id() -> str:
    """Return the owner's Discord user ID, or empty string if unknown.

    Tries discord_config first (the operational source of truth, set
    when the gateway was configured), then users.json as fallback
    (where role='owner' is the canonical record).
    """
    # Source 1: discord_config.owner_discord_id
    try:
        from core.services.discord_config import load_discord_config
        cfg = load_discord_config()
        if cfg:
            owner = str(cfg.get("owner_discord_id") or "").strip()
            if owner:
                return owner
    except Exception as exc:
        logger.debug("owner_resolver: discord_config read failed: %s", exc)

    # Source 2: users.json
    try:
        from core.identity.users import load_users
        for u in load_users():
            if getattr(u, "role", "") == "owner":
                return str(u.discord_id or "").strip()
    except Exception as exc:
        logger.debug("owner_resolver: users.json read failed: %s", exc)
    return ""


def is_owner_session(session: dict[str, Any] | None) -> bool:
    """Decide whether a session record belongs to the owner.

    Heuristics, ordered most-specific to most-permissive:
      1. session.user_id matches owner's discord_id (preferred — the
         multi-user routing layer stamps this)
      2. session.title matches the legacy "Discord DM" with no user
         suffix (pre-multi-user world; that one was always Bjørn's)
      3. session.title is "Discord DM — {owner_id}"
      4. session has any messages with the owner's user_id

    A session with no user_id and no Discord-related title falls
    through as "ambiguous" → False (refuse rather than risk leaking).
    """
    if not isinstance(session, dict):
        return False
    owner_id = get_owner_discord_id()
    if not owner_id:
        # Without a known owner we can't gate anything; refuse all
        # autonomous routing.
        return False
    # 1. session.user_id (if the schema carries it)
    sess_user_id = str(session.get("user_id") or "").strip()
    if sess_user_id and sess_user_id == owner_id:
        return True
    # 2/3. Title patterns
    title = str(session.get("title") or "").strip()
    if title == "Discord DM":
        return True  # legacy single-user title
    if title == f"Discord DM — {owner_id}":
        return True
    # 4. Inspect messages for owner-stamped user_id
    messages = session.get("messages")
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict):
                if str(m.get("user_id") or "").strip() == owner_id:
                    return True
    return False


def resolve_owner_target_session() -> str:
    """Find the session that an autonomous Bjørn-event should target.

    Order:
      1. Pinned session — but only if it's owner-owned
      2. Most recent owner-owned session from list_chat_sessions
      3. Empty string (caller should create a fresh session or skip)

    Never returns a member's session id. Returning empty is a
    deliberate "I refuse to dispatch into ambiguity" signal.
    """
    try:
        from core.services.notification_bridge import get_pinned_session_id
        from core.services.chat_sessions import get_chat_session, list_chat_sessions
    except Exception as exc:
        logger.warning("owner_resolver: chat-session imports failed: %s", exc)
        return ""

    owner_id = get_owner_discord_id()

    # Step 1: pinned, if owner-owned
    pinned = (get_pinned_session_id() or "").strip()
    if pinned:
        full = get_chat_session(pinned)
        if full and is_owner_session(full):
            return pinned
        # Pinned exists but isn't owner's — fall through, do NOT use it
        logger.info(
            "owner_resolver: pinned session %s is not owner-owned, "
            "ignoring for autonomous dispatch",
            pinned,
        )

    # Step 2: most recent owner-owned session.
    # list_chat_sessions accepts user_id filter (added when middleware
    # was wired). Try the filtered call first; if the implementation
    # doesn't honor the kwarg for some reason, fall back to manual
    # filtering.
    try:
        if owner_id:
            scoped = list_chat_sessions(user_id=owner_id)
        else:
            scoped = list_chat_sessions()
    except TypeError:
        scoped = list_chat_sessions()

    for s in scoped:
        sid = str((s or {}).get("id") or "").strip()
        if not sid:
            continue
        full = get_chat_session(sid)
        if not full:
            continue
        if not is_owner_session(full):
            # If the user_id filter didn't actually scope, double-check
            continue
        if any(m.get("role") == "user" for m in (full.get("messages") or [])):
            return sid

    return ""


def session_is_external_channel(session_id: str | None) -> bool:
    """True hvis sessionen er en EKSTERN kanal (Discord/Telegram) ud fra titlen.

    Bruges som guard så app/operator-wakeups aldrig kan re-engagere i en
    Discord-session (Bjørn 2026-06-13: wakeup landede på Discord i stedet for
    jarvis-desk). Fail-safe: ved tvivl returneres False (behandl som app), så
    vi ikke ved en fejl smider en legitim app-session væk.
    """
    sid = (session_id or "").strip()
    if not sid:
        return False
    try:
        from core.services.chat_sessions import get_chat_session, parse_channel_from_session_title
        full = get_chat_session(sid)
        title = (full or {}).get("title")
        return parse_channel_from_session_title(title)[0] in ("discord", "telegram")
    except Exception:
        return False


def _senest_aktive_app_session(sessions: list[Any] | None) -> str:
    """Sidste udvej: den senest opdaterede APP-session med bruger-beskeder.

    MÅLT 17/9-2026: 0 af 502 chat-sessioner er stemplet med owner's user_id —
    og ingen besked bærer den. Heuristikkerne i `is_owner_session` kan derfor
    strukturelt ikke matche, og `resolve_owner_app_session` svarede "" for
    enhver wakeup uden eksplicit session_id. De landede i en frisk
    «auto-wakeup-*»-session som ingen åbner: wakeup'en fyrede, svaret blev
    skrevet, og Bjørn så det aldrig (selvtest 17/9: selvtest-30s endte i
    `auto-wakeup-20260917`).

    Vi vælger derfor den senest opdaterede session der (a) ikke er en ekstern
    kanal, (b) har mindst én bruger-besked og (c) ikke selv er en autonom
    session. Discord/Telegram filtreres eksplicit, så guarden fra 13/6-2026
    står ved magt — fallback'en kan aldrig lække til en ekstern kanal.
    """
    from core.services.chat_sessions import (
        get_chat_session,
        parse_channel_from_session_title,
    )

    kandidater: list[tuple[str, str]] = []
    for s in sessions or []:
        sid = str((s or {}).get("id") or "").strip()
        if not sid or sid.startswith("auto-"):
            continue
        full = get_chat_session(sid)
        if not full:
            continue
        if parse_channel_from_session_title(full.get("title"))[0] in ("discord", "telegram"):
            continue
        if not any(m.get("role") == "user" for m in (full.get("messages") or [])):
            continue
        kandidater.append((str(full.get("updated_at") or ""), sid))

    if not kandidater:
        return ""
    kandidater.sort(reverse=True)
    valgt = kandidater[0][1]
    logger.warning(
        "owner_resolver(app): ingen owner-stemplet session fundet — falder "
        "tilbage til senest aktive app-session %s",
        valgt,
    )
    return valgt


def resolve_owner_app_session() -> str:
    """Som resolve_owner_target_session, men returnerer KUN en app/webchat-
    session — aldrig Discord/Telegram. Til wakeups der SKAL lande i jarvis-desk
    (operator_wakeup), så en autonom re-engagement ikke kan lække til Discord.

    Returnerer "" hvis ingen app-session findes → kalderen opretter en frisk
    (stadig in-app). Springer pinned over hvis den er en ekstern kanal.
    """
    try:
        from core.services.chat_sessions import get_chat_session, list_chat_sessions
        from core.services.notification_bridge import get_pinned_session_id
    except Exception as exc:
        logger.warning("owner_resolver(app): imports failed: %s", exc)
        return ""

    owner_id = get_owner_discord_id()

    pinned = (get_pinned_session_id() or "").strip()
    if pinned:
        full = get_chat_session(pinned)
        if full and is_owner_session(full) and not session_is_external_channel(pinned):
            return pinned
        # pinned er ekstern kanal eller ikke owner → fald igennem

    try:
        scoped = list_chat_sessions(user_id=owner_id) if owner_id else list_chat_sessions()
    except TypeError:
        scoped = list_chat_sessions()

    for s in scoped:
        sid = str((s or {}).get("id") or "").strip()
        if not sid:
            continue
        full = get_chat_session(sid)
        if not full or not is_owner_session(full):
            continue
        if session_is_external_channel(sid):
            continue  # GUARD: aldrig en ekstern kanal til en app-wakeup
        if any(m.get("role") == "user" for m in (full.get("messages") or [])):
            return sid

    # SIDSTE UDVEJ (17/9-2026): ingen owner-stemplet session matchede. Vi bruger
    # den Ufiltrerede liste — `scoped` er tom netop fordi intet er stemplet, så
    # et fallback på den ville også give "".
    try:
        alle = list_chat_sessions()
    except Exception:
        alle = []
    return _senest_aktive_app_session(alle)


def owner_user_id() -> str:
    """Ejerens `user_id` — det id hans egne beskeder er stemplet med.

    **To lagre, én sandhed der mangler i det ene.** Maalt paa CT105 24/9-2026:
    `users`-TABELLEN har 14 raekker, alle `role='member'`, og Bjoerns id
    `1246415163603816499` staar slet ikke i den. `users.json` har ham som
    `owner`. Et opslag der kun spoerger tabellen finder derfor ingen ejer —
    og det er ikke en teoretisk mangel:

    * `notifikations_emittere.system()` returnerer tomt uden en ejer, saa
      HVER «Ny version er klar» siden funktionen blev bygget er forsvundet.
      Maalt: 0 release-raekker i `notifikationer`, fra 0.6.43 til 0.6.94.
    * De autonome droemme-, hjerteslags- og vaeknings-sessioner skrives uden
      `user_id`, og sessionslisten kan kun vise en session hvis mindst én
      besked baerer den spoergendes id. 8534 beskeder usynlige.

    Derfor: tabellen foerst (den er den operationelle kilde naar den ER
    udfyldt), `users.json` som fald-tilbage. Denne funktion LÆSER kun — at
    skrive ejeren ind i tabellen er en identitets-aendring og hoerer ikke
    hjemme i et opslag.
    """
    # `users.json` FOERST. Kortlagt 24/9-2026: rollen bor autoritativt dér.
    #
    # De to lagre er en ufaerdig cutover fra juni med forskellige ansvar —
    # `users`-TABELLEN ejer login, tier, API-noegler og GDPR; `users.json` ejer
    # token-sub -> workspace + rolle. ALLE rolle-opslag i systemet gaar gennem
    # json: `workspace_context`, `run_profile`, `workspace_paths`,
    # `token_renewal`, `refresh_tokens`. Denne funktion var det ENESTE sted der
    # spurgte tabellen om en rolle, og den spurgte den foerst.
    #
    # Det virkede kun fordi tabellen ingen ejer-raekke har (14 raekker, alle
    # `member`). Dukkede der en op med et andet id, ville denne funktion
    # modsige hele resten af systemet. Rækkefoelgen er derfor vendt.
    try:
        from core.identity.users import load_users
        for u in load_users():
            if getattr(u, "role", "") == "owner":
                uid = str(getattr(u, "discord_id", "") or "").strip()
                if uid:
                    return uid
    except Exception as exc:
        logger.debug("owner_resolver: users.json kunne ikke laeses: %s", exc)

    # Tabellen som fald-tilbage: hvis cutoveren en dag goeres faerdig og rollen
    # flytter derind, finder vi ejeren alligevel.
    try:
        from core.runtime.db import connect
        with connect() as conn:
            raekke = conn.execute(
                "SELECT user_id FROM users WHERE role='owner' LIMIT 1").fetchone()
        if raekke and str(raekke[0] or "").strip():
            return str(raekke[0]).strip()
    except Exception as exc:
        logger.debug("owner_resolver: users-tabellen kunne ikke laeses: %s", exc)
    return ""
