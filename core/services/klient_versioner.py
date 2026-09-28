"""Hvilken udgave af appen sidder der i den anden ende?

## Hvorfor den findes

28/9-2026 gik der en time med at afgøre om en telefon kørte 218 eller 219.
Manifestet sagde hvad der var UDGIVET; ingen kunne sige hvad der var
INSTALLERET. Bjørn måtte spørges, og hverken jeg eller Jarvis kunne se det.

Det er en dum ting at gætte på, for klienten ved det selv. Den skal bare sige
det.

## Formen

Klienterne sender to hoveder på deres almindelige kald:

    X-Jarvis-Klient:        mobile | desk
    X-Jarvis-Klientversion: 0.2.120 (220)

Serveren skriver den SENESTE pr. klient. Ikke en historik: spørgsmålet er
«hvad kører der nu», og en tabel med en række pr. kald ville være endnu et
sted der vokser uden at nogen læser det.

Derfor heller ingen ny tabel — `state_store` findes med snesevis af brugere, og det her
er præcis dens slags: én nøgle, én værdi, sidst skrevet vinder.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

NOEGLE = "klient_versioner"

#: Hvad vi overhovedet tager imod. En header er brugerdata: uden en skranke
#: kunne hvem som helst skrive en roman ind i runtime-tilstanden.
_MAKS_LAENGDE = 64
_KLIENTER = ("mobile", "desk", "cli")
_TILLADT = re.compile(r"^[A-Za-z0-9 ._()+-]+$")


def _rent(vaerdi: str, tilladte: tuple[str, ...] = ()) -> str:
    v = str(vaerdi or "").strip()
    if not v or len(v) > _MAKS_LAENGDE or not _TILLADT.match(v):
        return ""
    if tilladte and v not in tilladte:
        return ""
    return v


def noter(klient: str, version: str) -> bool:
    """Skriv den seneste version for én klient. True hvis noget blev skrevet.

    Kaster aldrig: det her hænger på hver eneste request, og en app der
    rapporterer noget mærkeligt må ikke kunne vælte kaldet.
    """
    k = _rent(klient, _KLIENTER)
    v = _rent(version)
    if not k or not v:
        return False
    try:
        from core.runtime.state_store import load_json, save_json
        alle = load_json(NOEGLE, {})
        if not isinstance(alle, dict):
            alle = {}
        nu = datetime.now(timezone.utc).isoformat()
        tidligere = alle.get(k) or {}
        if isinstance(tidligere, dict) and tidligere.get("version") == v:
            # Samme version som sidst: opdatér kun tidsstemplet, så «sidst set»
            # stadig er sandt uden at vi skriver en ny værdi ved hvert kald.
            tidligere["sidst_set"] = nu
            alle[k] = tidligere
        else:
            alle[k] = {"version": v, "sidst_set": nu, "foerst_set": nu}
        save_json(NOEGLE, alle)
        return True
    except Exception:  # noqa: BLE001 — en version er ikke turen værd
        logger.warning("kunne ikke notere klientversion for %s", k, exc_info=True)
        return False


def alle() -> dict[str, Any]:
    """Hvad kører der lige nu, pr. klient. Tom dict hvis ingen har sagt det."""
    try:
        from core.runtime.state_store import load_json
        ud = load_json(NOEGLE, {})
        return ud if isinstance(ud, dict) else {}
    except Exception:  # noqa: BLE001
        logger.warning("kunne ikke laese klientversioner", exc_info=True)
        return {}
