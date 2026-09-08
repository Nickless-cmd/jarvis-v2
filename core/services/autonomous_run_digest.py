"""Referat af en autonom koersel — kort, i hans egen samtale.

Bjoern 8/9-2026: de autonome runs «ligger i en session for sig selv saa ser dem
ikke rigtigt». Han bad foerst om at flytte dem; tallene sagde nej:

    proaktive beskeder        2-4 pr. dag
    autonome runs             3-4 sessioner pr. dag
    auto-recurring-20260907   168 beskeder — heraf 155 TOOL-resultater

155 tool-beskeder i hans samtale ville baade drukne den og aede hans
prompt-kontekst. Saa: arbejdet bliver i sin egen session, og et REFERAT gaar
derhen hvor han er.

## Det pinger ikke

Referatet skrives direkte som en chat-besked i hans sidst aktive samtale — det
gaar IKKE gennem notifikations-broen. Tre-fire push om dagen for rutinearbejde
ville laere ham at ignorere kanalen, og den kanal skal blive ved at betyde
noget. Han ser referatet naar han kigger.

## Hvad der staar i det

Kun det han kan bruge: hvad koerslen var, hvad den roerte, og hvad den selv kom
frem til. Ikke tool-listen i sin fulde laengde — det var praecis dét der gjorde
sessionerne ulaeselige.

En koersel uden baade output og aendringer faar INTET referat. «Jeg koerte og
lavede ingenting» er stoej, og der er 3-4 af dem om dagen.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_MAKS_VAERKTOEJER = 5
_MAKS_FILER = 5
_MAKS_UDDRAG = 220

# Session-praefikserne er runtime'ens egne. Navnene er hans sprog, ikke
# maskinens: han skal kunne se hvad det VAR uden at slaa noget op.
_SLAGS = {
    "auto-dream": "Drømme",
    "auto-heartbeat": "Hjerteslag",
    "auto-recurring": "Tilbagevendende",
    "auto-wakeup": "Vækning",
    "auto-work": "Arbejde",
    "auto-autonomous": "Autonom",
}


def _slags_af(session_id: str) -> str:
    s = (session_id or "").lower()
    for praefiks, navn in _SLAGS.items():
        if s.startswith(praefiks):
            return navn
    return "Autonom"


def _foerste_afsnit(tekst: str) -> str:
    """Hans egen konklusion, ikke hele udskriften.

    Foerste hele saetning(er) op til `_MAKS_UDDRAG` tegn — klippet ved et
    saetningsskel, saa referatet ikke selv ender midt i et ord. Det var én af
    de laekager der stod i den proaktive kanal.
    """
    t = " ".join(str(tekst or "").split()).strip()
    if not t:
        return ""
    if len(t) <= _MAKS_UDDRAG:
        return t
    klip = t[:_MAKS_UDDRAG]
    skel = max(klip.rfind(". "), klip.rfind("! "), klip.rfind("? "))
    return (klip[:skel + 1] if skel > 60 else klip.rstrip()) + ("" if skel > 60 else " …")


def _pænt_vaerktoej(navn: str) -> str:
    return re.sub(r"[_-]+", " ", str(navn or "").strip()).strip()


def byg_referat(
    *,
    session_id: str,
    tool_calls: list[str] | None = None,
    output: str = "",
    aendrede_filer: list[str] | None = None,
    committet: bool = False,
) -> str:
    """Referatet, eller tom streng hvis der ikke er noget at fortaelle."""
    uddrag = _foerste_afsnit(output)
    filer = [f for f in (aendrede_filer or []) if f]
    if not uddrag and not filer:
        return ""      # «koerte og lavede ingenting» er stoej

    linjer = ["🌙 **%s** — hvad jeg lavede mens du var væk:" % _slags_af(session_id)]
    if uddrag:
        linjer.append("")
        linjer.append(uddrag)
    if filer:
        vist = filer[:_MAKS_FILER]
        rest = len(filer) - len(vist)
        linjer.append("")
        linjer.append("%s %s%s" % (
            "Committet:" if committet else "Ændrede:",
            ", ".join("`%s`" % f for f in vist),
            " (+%d mere)" % rest if rest > 0 else "",
        ))
    unikke = sorted({_pænt_vaerktoej(t) for t in (tool_calls or []) if t})
    if unikke:
        vist = unikke[:_MAKS_VAERKTOEJER]
        rest = len(unikke) - len(vist)
        linjer.append("")
        linjer.append("_Brugte: %s%s_" % (
            ", ".join(vist), " +%d" % rest if rest > 0 else ""))
    return "\n".join(linjer)


def post_referat(
    *,
    run_id: str,
    session_id: str,
    tool_calls: list[str] | None = None,
    output: str = "",
    aendrede_filer: list[str] | None = None,
    committet: bool = False,
) -> str:
    """Skriv referatet i hans sidst aktive samtale. Returnerer session_id ('' = intet skrevet).

    Self-safe og tavs: et referat der ikke naar frem maa aldrig kunne vaelte
    afslutningen af en koersel.
    """
    try:
        tekst = byg_referat(session_id=session_id, tool_calls=tool_calls, output=output,
                            aendrede_filer=aendrede_filer, committet=committet)
        if not tekst:
            return ""

        # Samme laekage-vaern som den proaktive kanal: et referat der citerer
        # maskineriet er lige saa ubrugeligt som en tanke der goer det.
        from core.services.thought_leak_guard import ligner_ikke_en_tanke
        if ligner_ikke_en_tanke(_foerste_afsnit(output)):
            tekst = byg_referat(session_id=session_id, tool_calls=tool_calls, output="",
                                aendrede_filer=aendrede_filer, committet=committet)
            if not tekst:
                return ""

        from core.services.proactivity_bridge import _sidst_aktive_samtale
        sid = _sidst_aktive_samtale()
        if not sid:
            return ""     # ingen frisk samtale → referatet ville ligge i en silo igen

        from core.services.chat_sessions import append_chat_message
        append_chat_message(session_id=sid, role="assistant", content=tekst,
                            workspace_name="default")
        logger.info("autonomous_run_digest: referat for %s → %s", run_id[:12], sid)
        return sid
    except Exception:
        logger.debug("autonomous_run_digest: kunne ikke poste referat", exc_info=True)
        return ""
