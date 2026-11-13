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


_MIN_SAETNING = 60


def _luk_markdown(t: str) -> str:
    """Fjern en uafsluttet markdown-token fra halen.

    Maalt 9/11-2026: de referater Bjoern fik, indeholdt `**` og backtick der
    aldrig blev lukket («Posten `visib», «Felt-te…»), fordi klippet faldt inde
    i markdown'en. En aaben token er ikke et forkortet citat — den er en
    skaaret konstruktion, og den skal fjernes, ikke vises.
    """
    while True:
        if t.count("`") % 2 == 1:
            t = t[: t.rfind("`")].rstrip()
            continue
        if t.count("**") % 2 == 1:
            t = t[: t.rfind("**")].rstrip()
            continue
        return t


def _klippet_paent(t: str) -> str:
    """Trim halen til sidste HELE ord og markér at noget blev skaaret."""
    mellemrum = t.rfind(" ")
    if mellemrum > _MIN_SAETNING:
        t = t[:mellemrum]
    t = t.rstrip(" ,;:—–-")
    return (t + " …") if t else t


def _foerste_afsnit(tekst: str) -> str:
    """Hans egen konklusion, ikke hele udskriften.

    Klippet ved et saetningsskel; findes der intet saadant efter
    `_MIN_SAETNING`, klippes der ved sidste hele ord. Aldrig midt i et ord, og
    aldrig inde i en markdown-token.

    Maalt 9/11-2026 (fix): den gamle fallback klippede raat ved 220 tegn. Alle
    seks seneste referater endte midt i et ord, og `**`/backtick stod aabent.
    """
    t = " ".join(str(tekst or "").split()).strip()
    if not t:
        return ""
    klippet = False
    if len(t) > _MAKS_UDDRAG:
        klip = t[:_MAKS_UDDRAG]
        skel = max(klip.rfind(". "), klip.rfind("! "), klip.rfind("? "))
        if skel > _MIN_SAETNING:
            t = klip[: skel + 1]
        else:
            t = _klippet_paent(klip)
            klippet = True
    foer = t
    t = _luk_markdown(t)
    if t != foer:
        t = _klippet_paent(t)
        klippet = True
    if klippet and not t.endswith("…"):
        t = t + " …"
    return t


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
    """Læg referatet i INDBOKKEN. Returnerer postens kilde-id ('' = intet skrevet).

    ## Hvorfor ikke chatten (ændret 13/11-2026)

    Før skrev denne gennem `send_session_notification` til den sidst aktive
    samtale. Målt: **18 baggrundsrun i døgnet gav 18 «🌙 Hjerteslag»-klumper
    midt i samtalen.** Bjørn: «jeg er sku lidt i tvivl om hjeret slaget bruges
    rigtigt» — og det var han, fordi fladen kaldte to forskellige ting det
    samme: den ægte puls (`heartbeat.phased_tick`) og post-run-rapporter der
    ikke havde noget med samtalen at gøre.

    Rapporten hører i indbakken, fordi indbakken har et VÆRN: den kan sige
    «der er noget nyt» i stedet for at dumpe indhold. Chatten er stedet hvor
    vi taler — ikke en log vi begge skal læse os igennem.

    ## Kontrakten

    Kildetypen er `digest`, som staar i `IKKE_GATENDE_KILDETYPER`: posten er
    SYNLIG i prompten under «REFERATER (til orientering)» men kan aldrig
    naegte en mutation. `importance="normal"` med vilje — et referat skal
    ikke fortrænge en post der faktisk kræver noget.

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

        from core.services.inbox_state import _ejer_id, registrer_kilde

        ejer = _ejer_id()
        if not ejer:
            # Uden en ejer kan posten ikke placeres — og en post uden ejer
            # ville havne i den forkerte indbakke. Tavst fravalg er rigtigt
            # her; kalderen er en afslutnings-hook der ikke maa vaelte.
            logger.debug("autonomous_run_digest: ingen ejer — referat ikke skrevet")
            return ""

        from datetime import UTC as _UTC
        from datetime import datetime as _dt
        from datetime import timedelta as _td

        kilde_id = f"referat-{run_id}"
        svar = registrer_kilde(
            bruger_id=ejer,
            kildetype="digest",
            kilde_id=kilde_id,
            oprettende_run_id=run_id,
            beskrivelse=tekst[:600],
            session_id=session_id,
            importance="normal",
            # Syv dage: en orientering der er ældre end en uge er historie,
            # og historie hører i sessionsloggen — ikke i indbakken.
            expires_at=(_dt.now(_UTC) + _td(days=7)).isoformat(),
        )
        status = str((svar or {}).get("status") or "")
        if status != "ok":
            logger.warning(
                "autonomous_run_digest: referat ikke placeret for %s: %s",
                run_id[:12], svar)
            return ""
        logger.info("autonomous_run_digest: referat for %s → indbakke (%s)",
                    run_id[:12], svar.get("post_id") or svar.get("id") or "ok")
        return kilde_id
    except Exception:
        logger.debug("autonomous_run_digest: kunne ikke poste referat", exc_info=True)
        return ""
