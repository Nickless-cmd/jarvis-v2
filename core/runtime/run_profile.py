"""Hvilken profil koerer en given koersel under — Fase 9.

Exit-kriteriet siger: «every run records effective profile schema version and
hash». Foer det kan ske, skal der findes et svar paa hvilken profil en koersel
HOERER til. Det svar er i dag spredt ud over flere flag paa `VisibleRun` —
`autonomous`, `local_tool_exec`, `trust_all` — og ingen af dem hedder «profil».

Denne fil er det ene sted hvor de flag bliver til ét navn.

## Hvorfor det ikke bare er et opslag paa `lane`

Fordi lane er hvilken MODEL-pulje koerslen bruger, ikke hvilke regler den
arbejder under. To koersler i samme lane kan have vidt forskellige rettigheder:
Bjoerns egen tur og et baggrunds-heartbeat ligger begge i `primary`.

## Raekkefoelgen er ikke tilfaeldig

Den gaar fra mest til mindst specifik, og enhver tvivl falder nedad. Et run der
baade er autonomt OG har local_tool_exec er et autonomt run — fordi «ingen
mennesker til stede» er den stramme egenskab, og den skal vinde.
"""
from __future__ import annotations

from typing import Any

from core.runtime.profile_composer import EffektivProfil
from core.runtime.profiles import byg


def profil_navn_for(run: Any, *, research: bool = False) -> str:
    """Profilnavnet for en koersel. Falder altid ud i noget kendt."""
    try:
        if bool(getattr(run, "autonomous", False)):
            return "autonomous"
        if research:
            return "research"
        if bool(getattr(run, "local_tool_exec", False)):
            return "jarvis-code"
        return _synlig_profil(run)
    except Exception:
        # Kan vi ikke afgoere det, er svaret ikke «den mest tilladte».
        return "safe-offline"


def _synlig_profil(run: Any) -> str:
    """Ejeren eller et husstandsmedlem?

    Rollen kommer fra workspace-konteksten, ikke fra koerslen — en koersel kan
    ikke udnaevne sig selv til ejer.
    """
    try:
        from core.identity.workspace_context import effective_role
        rolle = (effective_role() or "").strip().lower()
    except Exception:
        rolle = ""
    return "visible-owner" if rolle == "owner" else "visible-member"


def profil_for(run: Any, *, research: bool = False,
               overstyring: dict[str, Any] | None = None) -> EffektivProfil:
    """Den effektive profil for en koersel — klar til at gemmes paa raekken."""
    return byg(profil_navn_for(run, research=research), overstyring=overstyring)
