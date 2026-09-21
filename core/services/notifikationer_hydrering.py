# core/services/notifikationer_hydrering.py
"""Feedens laesning — den slaar op hos EJEREN, ikke i sin egen kopi.

Det er designets kerne. En godkendelse der er afgjort paa telefonen lukker sig
selv her, og desk-feeden helbreder sig selv ved naeste laesning. En kopi ville
have det spoegelse indbygget: man kunne staa og godkende noget der var vaek.

En hydrering der FEJLER lukker ikke raekken. En utilgaengelig ejer maa ikke se
ud som en klaret opgave — saa ville en nedetid tomme feeden.
"""
from __future__ import annotations

import logging
from typing import Any

from core.services import notifikationer as _lager

_log = logging.getLogger(__name__)

#: Slags man kan svare paa direkte i fladen.
#:
#: KUN `approval`. `question` (pause_and_ask) besvares med en TEKST eller et af
#: Jarvis' egne valg, sendt som en besked i samtalen — der findes ingen
#: server-side afgoerelse at kalde. Spoergsmaals-raekken foerer i stedet hen til
#: samtalen. Specen sagde oprindeligt begge; kaldestedet sagde noget andet.
AFGOERBARE = {"approval"}


def _hydrer_approval(raekke: dict[str, Any]) -> dict[str, Any] | None:
    """None = ejeren er faerdig, luk raekken. Kaster = ejeren er utilgaengelig."""
    from core.services import approval_runtime
    kort = approval_runtime.state(str(raekke["ref"] or ""))
    if not kort:
        return None
    if str(kort.get("status") or "") != "pending":
        return None
    vaerktoej = str(kort.get("tool_name") or "et værktøj")
    return {"titel": f"Vil du tillade {vaerktoej}?",
            "tekst": str(kort.get("summary") or raekke["tekst"] or "")}


def _hydrer(raekke: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """(felter, foraeldet). felter=None betyder «luk raekken»."""
    kilde = str(raekke["kilde"])
    if kilde == "egen":
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    try:
        if kilde == "approval":
            return _hydrer_approval(raekke), False
        # `run` og `event` hydreres i Task 6, hvor deres emittere bygges. Indtil
        # da staar de paa deres gemte tekst frem for at forsvinde.
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    except Exception:
        _log.warning("notifikation %s: ejeren (%s) kunne ikke naas",
                     raekke["id"], kilde, exc_info=True)
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, True


def feed(user_id: str, *, er_owner: bool) -> list[dict[str, Any]]:
    """Aabne notifikationer, hydreret hos deres ejere."""
    ud: list[dict[str, Any]] = []
    for raekke in _lager.aabne(user_id, er_owner=er_owner):
        felter, foraeldet = _hydrer(raekke)
        if felter is None:
            _lager.luk(str(raekke["id"]), "superseded")
            continue
        ud.append({
            "id": raekke["id"],
            "slags": raekke["slags"],
            "titel": felter["titel"],
            "tekst": felter["tekst"],
            "session_id": raekke["session_id"],
            "oprettet": raekke["oprettet"],
            "kan_afgoere": raekke["slags"] in AFGOERBARE and not foraeldet,
            "foraeldet": foraeldet,
        })
    return ud
