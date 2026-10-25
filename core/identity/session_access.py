"""Må den der spørger, røre DENNE samtale?

Bjørn 19/9-2026: «luk hullet i de gamle». Samtale-ruterne — hent, følg,
omdøb, fastgør/arkivér, slet, fork, spol tilbage — tjekkede ikke hvem
samtalen tilhørte. Enhver med et gyldigt token kunne læse eller slette en
andens samtale, hvis de kendte id'et.

## Reglen

- **Ejeren må alt.** Det er hans server; de andres arbejdsrum er krypteret
  i forvejen, og han er den der skal kunne rydde op.
- **Alle andre må kun deres egne samtaler.** Ejeren kommer fra den seneste
  stemplede BRUGERbesked; assistant/tool-rækker kan have proces-identitet og
  må ikke overtage samtalen. Sammenlignet på ARBEJDSRUM, ikke
  på rå id: målt på CT105 findes Bjørns samtaler under tre stempler
  (hans Discord-id, `bjorn`, `system`), og et id-for-id-tjek ville have
  låst ham ude af 47 af sine egne.
- **Ustemplede (legacy) samtaler** har ingen ejer at tjekke imod og er åbne,
  som før. Ingen af dem er blandede: målt 0 samtaler med beskeder fra mere
  end én bruger.
- **Intet bruger-kontekst** (interne kald, enkeltbruger-dev) → åbent, som før.

Rollen læses med `current_role()`, ikke `effective_role()`: sidstnævnte
fornyer et TOTP-override-vindue som sideeffekt, og et adgangstjek må ikke
ændre noget.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = [
    "maa_tilgaa_session",
    "arbejdsrum_for",
    "identitetsaliaser_for_bruger",
    "ejerstempel_tilhoerer_bruger",
    "session_tilhoerer_bruger",
]


def identitetsaliaser_for_bruger(uid: str) -> tuple[str, ...]:
    """Rå og kanoniske id'er der beviseligt tilhører samme bruger."""
    token = (uid or "").strip()
    if not token:
        return ()
    aliases = {token}
    try:
        from core.services.routine_migration import (
            canonical_identity_aliases,
            resolve_canonical_identity,
        )
        canonical = resolve_canonical_identity(token)
        if canonical:
            aliases.update(canonical_identity_aliases(canonical))
    except Exception:
        logger.debug("session_access: aliasopslag af %s fejlede", token, exc_info=True)
    return tuple(sorted(aliases))


def arbejdsrum_for(uid: str) -> str:
    """Det arbejdsrum et bruger-stempel hører til.

    Et kendt id (Discord/token) giver brugerens workspace. Ellers er stemplet
    selv arbejdsrummet — de ældre beskeder blev stemplet med workspace-navnet
    (`bjorn`) frem for id'et.
    """
    u = (uid or "").strip()
    if not u:
        return ""
    try:
        from core.identity.users import find_user_by_discord_id
        bruger = find_user_by_discord_id(u)
        if bruger is not None and getattr(bruger, "workspace", ""):
            return str(bruger.workspace)
    except Exception:
        logger.debug("session_access: opslag af %s fejlede", u, exc_info=True)
    try:
        from core.runtime import db
        from core.services.routine_migration import resolve_canonical_identity
        canonical = resolve_canonical_identity(u)
        row = db.get_user_row(canonical) if canonical else None
        if row and row.get("workspace"):
            return str(row["workspace"])
    except Exception:
        logger.debug("session_access: kanonisk opslag af %s fejlede", u, exc_info=True)
    return u


def ejerstempel_tilhoerer_bruger(owner_user_id: str, user_id: str) -> bool:
    """Har et ejer-stempel samme arbejdsrum som brugeren?"""
    ejer = (owner_user_id or "").strip()
    bruger = (user_id or "").strip()
    if not ejer or not bruger:
        return True
    return arbejdsrum_for(ejer) == arbejdsrum_for(bruger)


def session_tilhoerer_bruger(session_id: str, user_id: str) -> bool:
    """Har seneste stemplede brugerbesked samme arbejdsrum som brugeren?

    Ustemplede legacy-samtaler bevarer den hidtidige åbne adgang. Hjælperen
    bruges både af adgangsgaten og sessionslisten, så listen ikke tilbyder en
    samtale som efterfølgende bliver afvist ved åbning eller afsendelse.
    """
    sid = (session_id or "").strip()
    bruger = (user_id or "").strip()
    if not sid or not bruger:
        return True
    from core.services.chat_sessions import get_session_owner
    return ejerstempel_tilhoerer_bruger(get_session_owner(sid) or "", bruger)


def maa_tilgaa_session(session_id: str) -> bool:
    """Må den nuværende bruger læse eller ændre samtalen?"""
    sid = (session_id or "").strip()
    if not sid:
        return True
    from core.identity.workspace_context import current_role, current_user_id
    if (current_role() or "") == "owner":
        return True
    bruger = (current_user_id() or "").strip()
    if not bruger:
        return True
    return session_tilhoerer_bruger(sid, bruger)
