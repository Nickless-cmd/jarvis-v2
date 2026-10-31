"""Må den der spørger, bruge code mode? — reglen fra Codex' fjernstyring.

Bjørn 19/9-2026 (codex-remote-control.md §9): «Code mode i mobil-appen er først
tilgængeligt for en samtale, når den enhed der skal se den er korrekt tilføjet
i desk». Code mode kan køre kommandoer, læse og skrive filer — på serveren og,
via broen, på hans egen computer. Det skal kræve mere end et gyldigt token.

Slukket (standard): alt som før. Tændt (`db_devices.kraev_aktivt`): tokenet
skal matche en AKTIV enhed for brugeren — en parret telefon (claim `enhed`)
eller en registreret desk-installation (claim `app_id`).

**Reglen gælder kun ejeren** (31/10-2026). Den værner om Bjørns maskine, og
målingen viste at den i praksis spærrede hele jarvis-code-klienten for
medlemmer uden at værne om noget: `enheder` havde 5 rækker og alle var hans.
Et medlem slipper derfor igennem uden enheds-opslag. Kan ejeren ikke slås op,
håndhæves reglen for alle — en undtagelse vi ikke kan afgrænse må ikke gælde
nogen.

Kald uden bruger-kontekst (interne kald, enkeltbruger-dev) er uberørte, som i
`session_access`: reglen handler om klienter, ikke om Jarvis selv.
"""
from __future__ import annotations

__all__ = ["kode_tilladt", "KODE_NAEGTET"]

KODE_NAEGTET = (
    "Code mode kræver at denne enhed er tilføjet i desk: Indstillinger → "
    "Konto → Enheder (med din totrinskode). Bruger du en anden klient — fx "
    "jarvis-code — findes den flade ikke der: registrér enheden med din "
    "totrinskode mod POST /auth/enheder/denne-computer, så får klienten et "
    "token med det app_id som reglen matcher."
)


def kode_tilladt() -> bool:
    try:
        from core.identity.workspace_context import current_token_enhed, current_user_id
        bruger = (current_user_id() or "").strip()
        # Interne/dev-kald er uden bruger og skal være uberørte, også mens
        # enhedsregistret er utilgængeligt. Tjek identiteten FØR DB-opslaget;
        # ellers kunne en stale test-/shutdown-DB gøre et internt kald til 403.
        if not bruger:
            return True
        from core.runtime.db_devices import kraev_aktivt, maa_bruge_kode
        if not kraev_aktivt():
            return True

        # Enheds-reglen værner om EJERENS maskine — ikke om medlemmernes
        # klienter. Målt 31/10-2026: `enheder` havde 5 rækker og ALLE var
        # ejerens; intet medlem har nogensinde haft en code-samtale. Reglen
        # spærrede derfor hele jarvis-code-klienten for alle andre, uden at
        # værne om noget: den kunne ikke skelne «fjernstyr Bjørns maskine»
        # fra «kør kode på sin egen». Et medlem der kører kode på sin EGEN
        # maskine er ikke den trussel reglen blev skrevet imod.
        #
        # Kan ejeren ikke slås op, håndhæves reglen for ALLE: en undtagelse
        # vi ikke kan afgrænse, må ikke gælde nogen. Det er den ene retning
        # der ikke kan gøre skade — den anden ville stille og roligt afskaffe
        # reglen for den person den findes for.
        from core.identity.owner_resolver import owner_user_id

        ejer = (owner_user_id() or "").strip()
        if ejer and bruger != ejer:
            return True

        enhed, app_id = current_token_enhed()
        return maa_bruge_kode(bruger, enhed=enhed, app_id=app_id)
    except Exception:
        # Registret utilgængeligt mens reglen er TÆNDT: fail-closed. En regel
        # der åbner når databasen hikker, er ingen regel.
        return False
