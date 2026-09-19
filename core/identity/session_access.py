"""Må den der spørger, røre DENNE samtale?

Bjørn 19/9-2026: «luk hullet i de gamle». Samtale-ruterne — hent, følg,
omdøb, fastgør/arkivér, slet, fork, spol tilbage — tjekkede ikke hvem
samtalen tilhørte. Enhver med et gyldigt token kunne læse eller slette en
andens samtale, hvis de kendte id'et.

## Reglen

- **Ejeren må alt.** Det er hans server; de andres arbejdsrum er krypteret
  i forvejen, og han er den der skal kunne rydde op.
- **Alle andre må kun deres egne samtaler.** Sammenlignet på ARBEJDSRUM, ikke
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

__all__ = ["maa_tilgaa_session", "arbejdsrum_for"]


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
    return u


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
    from core.services.chat_sessions import get_session_owner
    ejer = (get_session_owner(sid) or "").strip()
    if not ejer:
        return True
    return arbejdsrum_for(ejer) == arbejdsrum_for(bruger)
