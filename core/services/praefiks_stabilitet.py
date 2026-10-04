"""Bliver de «uændrede» præfiks-sektioner ved med at være uændrede?

Bjørn 4/10-2026, efter at fire hale-sektioner blev flyttet op i det cachede
præfiks: «byg den».

## Hvorfor vagten er nødvendig

Flytningen var en nettogevinst udelukkende fordi de fire målte **nul**
ændringer over 99 ture. Regnestykket er skarpt, og det er ikke symmetrisk:

    sparer   900 tokens × 99 ture × $0,147/M  =  $0,0131
    koster   ÉN ændring: 120.064 tokens cache-miss  =  $0,0176

Et skift sidst i præfikset invaliderer nemlig ikke kun sektionen — det
invaliderer **hele samtalehistorikken ovenpå**, fordi cachen matcher på
længste fælles præfiks og alt efter divergenspunktet falder ud.

Så **én ændring per 99 ture gør flytningen til et tab.** Uden en vagt ville
det ske i tavshed: prompten ville se helt rigtig ud, og det eneste spor var en
regning der langsomt voksede.

## Hvad den gør, og hvad den ikke gør

Den sammenligner hver sektions fingeraftryk med sidste tur og siger til når
et ændrer sig. Den flytter ikke selv noget tilbage — det er en beslutning om
prompt-indhold, og den hører hos Bjørn.

Tilstanden er proces-lokal. En genstart nulstiller den, så en ændring der
falder præcis henover en genstart ses ikke. Det er bevidst: alternativet er en
DB-skrivning på prompt-samlingens varmeste sti, og vagten skal fange en
TENDENS over timer, ikke hver enkelt hændelse.

## Kontrakt

Som resten af måleværktøjet: kaster aldrig, holder kun et lille dict, og et
instrument der kan vælte det det måler er værre end ingen måling.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

#: navn -> (fingeraftryk, antal skift set i denne proces)
_set: dict[str, tuple[str, int]] = {}

#: Loft, saa en omdoebt sektion ikke kan vokse dictet i det uendelige.
_MAKS = 32


def _fingeraftryk(tekst: str) -> str:
    return hashlib.sha256(str(tekst or "").encode("utf-8")).hexdigest()[:16]


def tjek(sektioner: list[tuple[str, str]]) -> str:
    """Sammenlign med sidste tur. Returnér felter til timing-linjen.

    `sektioner` er (navn, tekst). Navnet er markøren fra `_STABILE_I_HALEN`,
    så loggen peger på præcis den sektion der skal flyttes tilbage.

    Tom streng ved enhver fejl — linjen skal stadig kunne skrives.
    """
    try:
        skift_nu: list[str] = []
        for navn, tekst in sektioner or []:
            n = str(navn or "").strip()
            if not n:
                continue
            fa = _fingeraftryk(tekst)
            foer = _set.get(n)
            if foer is None:
                if len(_set) < _MAKS:
                    _set[n] = (fa, 0)
                continue
            if foer[0] != fa:
                antal = foer[1] + 1
                _set[n] = (fa, antal)
                skift_nu.append(n)
                # WARNING og ikke info: det her ANDRER regnestykket bag en
                # beslutning der allerede er truffet. Én aendring per 99 ture
                # goer flytningen til et tab.
                logger.warning(
                    "praefiks_stabilitet: «%s» aendrede sig i praefikset "
                    "(%d. gang i denne proces). Et skift her koster hele "
                    "samtalehistorikken i cache-miss — overvej at flytte den "
                    "tilbage i halen.", n, antal)
        ud = [f"stabile={len(_set)}"]
        i_alt = sum(a for _f, a in _set.values())
        ud.append(f"stabil_skift={i_alt}")
        if skift_nu:
            # Navnet med paa linjen, saa det kan filtreres uden at laese logs.
            ud.append("stabil_skiftede=" + ",".join(
                n.split()[-1].strip("()") or n for n in skift_nu)[:120])
        return " ".join(ud)
    except Exception as exc:  # noqa: BLE001
        logger.debug("praefiks_stabilitet: tjekket fejlede: %s", exc)
        return ""


def nulstil() -> None:
    """Glem alt. Kun til tests — produktionen nulstiller ved genstart."""
    _set.clear()


__all__ = ["tjek", "nulstil"]
