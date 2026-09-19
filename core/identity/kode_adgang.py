"""Må den der spørger, bruge code mode? — reglen fra Codex' fjernstyring.

Bjørn 19/9-2026 (codex-remote-control.md §9): «Code mode i mobil-appen er først
tilgængeligt for en samtale, når den enhed der skal se den er korrekt tilføjet
i desk». Code mode kan køre kommandoer, læse og skrive filer — på serveren og,
via broen, på hans egen computer. Det skal kræve mere end et gyldigt token.

Slukket (standard): alt som før. Tændt (`db_devices.kraev_aktivt`): tokenet
skal matche en AKTIV enhed for brugeren — en parret telefon (claim `enhed`)
eller en registreret desk-installation (claim `app_id`).

Kald uden bruger-kontekst (interne kald, enkeltbruger-dev) er uberørte, som i
`session_access`: reglen handler om klienter, ikke om Jarvis selv.
"""
from __future__ import annotations

__all__ = ["kode_tilladt", "KODE_NAEGTET"]

KODE_NAEGTET = (
    "Code mode kræver at denne enhed er tilføjet i desk. Tilføj den under "
    "Indstillinger → Konto → Enheder på computeren (med din totrinskode)."
)


def kode_tilladt() -> bool:
    try:
        from core.runtime.db_devices import kraev_aktivt, maa_bruge_kode
        if not kraev_aktivt():
            return True
        from core.identity.workspace_context import current_token_enhed, current_user_id
        bruger = (current_user_id() or "").strip()
        if not bruger:
            return True
        enhed, app_id = current_token_enhed()
        return maa_bruge_kode(bruger, enhed=enhed, app_id=app_id)
    except Exception:
        # Registret utilgængeligt mens reglen er TÆNDT: fail-closed. En regel
        # der åbner når databasen hikker, er ingen regel.
        return False
