"""Skygge-taellere der overlever en genstart.

Alle tre skygger gjorde det samme: holdt taellere i hukommelsen og skrev de
ABSOLUTTE tal til `shared_cache`. Set 9/9-2026: kontrakt-skyggen viste 35
maalte kald, jeg deployede, og naeste aflaesning viste 1.

To fejl i én:

  * Genstart nulstiller hukommelsen, og foerste observation bagefter
    OVERSKRIVER det akkumulerede tal i cachen med det friske.
  * `jarvis-api` og `jarvis-runtime` er to processer der skriver samme
    noegle. Den sidste vinder; den andens maaling forsvinder.

Begge betyder at «skyggen har maalt X over flere dage» ikke kan siges — og
det er praecis den saetning en beslutning om at HAANDHAEVE skal hvile paa.

Loesningen er at gemme DELTAER frem for totaler: laes, laeg til det der er
sket siden sidste gemning, skriv. Saa er en genstart et hul paa nul, og to
processer laegger sammen frem for at overskrive hinanden.
"""
from __future__ import annotations

from typing import Any

_TTL = 7 * 24 * 3600.0


def flet(noegle: str, aktuelle: dict[str, int], sidst_gemt: dict[str, int],
         *, ekstra: dict[str, Any] | None = None, ttl: float = _TTL) -> None:
    """Laeg dette runs tilvaekst oveni det der allerede staar i cachen.

    `sidst_gemt` opdateres in-place, saa naeste kald kun tilfoejer det nye.
    Kaster aldrig: en taeller maa ikke kunne vaelte det den taeller.
    """
    try:
        from core.services import shared_cache
        gemt = shared_cache.get(noegle)
        samlet: dict[str, Any] = dict(gemt) if isinstance(gemt, dict) else {}
        for k, v in aktuelle.items():
            tilvaekst = int(v) - int(sidst_gemt.get(k, 0))
            if tilvaekst:
                samlet[k] = int(samlet.get(k, 0) or 0) + tilvaekst
            elif k not in samlet:
                samlet[k] = int(samlet.get(k, 0) or 0)
        if ekstra:
            samlet.update(ekstra)
        shared_cache.set(noegle, samlet, ttl_seconds=ttl)
        sidst_gemt.clear()
        sidst_gemt.update({k: int(v) for k, v in aktuelle.items()})
    except Exception:
        pass
