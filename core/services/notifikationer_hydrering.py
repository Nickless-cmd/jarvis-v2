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

#: Udfald -> den saetning fladen viser i historikken.
#:
#: Ukendte udfald falder tilbage til «Klaret» frem for at forsvinde: et nyt
#: udfald skal kunne SES med det samme nogen skriver det, ikke skjules indtil
#: nogen husker at opdatere denne tabel. En tavs historik er vaerre end en
#: upraecis en.
_UDFALD_TEKST = {
    "godkendt": "Godkendt af dig",
    "afvist": "Afvist af dig",
    "seen": "Lukket af dig",
    "superseded": "Klaret",
}


def _hydrer_approval(raekke: dict[str, Any]) -> dict[str, Any] | None:
    """None = ejeren er faerdig, luk raekken. Kaster = ejeren er utilgaengelig."""
    from core.services import approval_runtime
    kort = approval_runtime.state(str(raekke["ref"] or ""))
    if not kort:
        return None
    if str(kort.get("status") or "") != "pending":
        return None
    vaerktoej = str(kort.get("tool_name") or "et værktøj")
    # Kortet (approval_runtime.build_request) baerer INGEN beskrivelses-tekst —
    # kun tool_name, arguments, run_id/session_id, ejer og digest (se
    # PAAKRAEVEDE i approval_runtime.py). Der er derfor intet at hente hos
    # ejeren udover titlen; teksten bliver ved den gemte kopi.
    return {"titel": f"Vil du tillade {vaerktoej}?",
            "tekst": str(raekke["tekst"] or "")}


def _hydrer_run(raekke: dict[str, Any]) -> dict[str, Any] | None:
    """None = koerslen er ikke laengere i den tilstand der skabte raekken.

    K3 (2026-09-22): brugte foer en lokal `("failed", "interrupted")` der
    ikke daekkede `failed_terminal` — en status `status_for_run()` (den RAA
    DB-status) rent faktisk returnerer. Emitteren i
    `run_finalization.finalize_in_flight` fyrer PAA `failed_terminal`, saa en
    raekke blev skabt og lukket ved foerste laesning. Deler nu
    `KOERSEL_FEJLET_STATUS` med den fil, saa de to lister ikke kan skride fra
    hinanden igen."""
    from core.services.visible_runs_sections.run_finalization import (
        KOERSEL_FEJLET_STATUS, status_for_run, svar_for_run,
    )
    tilstand = status_for_run(str(raekke["ref"] or ""))
    slags = str(raekke["slags"])
    if slags == "run_failed" and tilstand not in KOERSEL_FEJLET_STATUS:
        return None
    if slags == "run_done" and tilstand not in ("completed", "done"):
        return None
    if slags == "run_done":
        # SVARET, ikke titlen. Raekken blev foedt med en titel («Svar klar i
        # «hey..»») og en TOM tekst, saa fladen kunne sige at der var et svar
        # uden at kunne vise det (Bjoern 26/9-2026: «hvor svar du skriver …
        # bliver vist der»). Teksten ligger hos ejeren — `visible_runs`
        # `.text_preview` — og hentes her, i samme aand som godkendelsens
        # hydrering: raekken PEGER paa sin ejer, den kopierer ham ikke.
        #
        # Er svaret tomt, falder vi tilbage til den gemte tekst frem for at
        # vise et tomt kort. En koersel kan ende uden at have skrevet noget
        # (afbrudt straks efter start), og «Svar klar» uden et svar er stadig
        # sandt — men et kort med en tom krop ser ud som en fejl.
        svar = svar_for_run(str(raekke["ref"] or ""))
        if svar:
            return {"titel": raekke["titel"], "tekst": svar}
    return {"titel": raekke["titel"], "tekst": raekke["tekst"]}


def _hydrer(raekke: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    """(felter, foraeldet). felter=None betyder «luk raekken»."""
    kilde = str(raekke["kilde"])
    if kilde == "egen":
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    try:
        if kilde == "approval":
            return _hydrer_approval(raekke), False
        if kilde == "run":
            return _hydrer_run(raekke), False
        # `event` hydreres senere. Indtil da staar den paa sin gemte tekst
        # frem for at forsvinde.
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, False
    except Exception:
        _log.warning("notifikation %s: ejeren (%s) kunne ikke naas",
                     raekke["id"], kilde, exc_info=True)
        return {"titel": raekke["titel"], "tekst": raekke["tekst"]}, True


def feed(user_id: str, *, er_owner: bool,
         aktiv_session: str | None = None) -> list[dict[str, Any]]:
    """Aabne notifikationer, hydreret hos deres ejere.

    `aktiv_session` (Bjoern 26/9-2026): den samtale brugeren SIDDER I lige nu.
    Svar fra den springes over — man laeser dem allerede i vinduet ved siden
    af, og en «Svar klar»-klokke for det man har foran sig er ren stoejfyld.

    Kun `run_done` filtreres. En GODKENDELSE i den aktive samtale skal
    fortsat vises: den venter paa et svar, og at skjule den ville betyde at
    man ikke kunne svare paa den flade man sidder i. Det er forskellen
    mellem «du har allerede set dette» og «du skal goere noget her».
    """
    # Afstemningen foerst: en ventende godkendelse uden raekke skal med i
    # SAMME laesning, ellers ville den foerst dukke op naeste gang.
    try:
        from core.services.notifikations_emittere import afstem_godkendelser
        afstem_godkendelser(user_id)
    except Exception:
        # En afstemning der fejler maa ikke tomme feeden for alt det andet.
        _log.warning("godkendelser kunne ikke afstemmes for %s", user_id, exc_info=True)
    ud: list[dict[str, Any]] = []
    for raekke in _lager.aabne(user_id, er_owner=er_owner):
        # Filtreringen ligger FOER hydreringen: den er billig, og et svar vi
        # alligevel kaster vaek skal ikke koste et DB-opslag hos ejeren.
        if (aktiv_session and str(raekke["slags"]) == "run_done"
                and str(raekke["session_id"] or "") == aktiv_session):
            continue
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


def tidligere(user_id: str, *, er_owner: bool, dage: int = 7) -> list[dict[str, Any]]:
    """KLAREDE notifikationer — ren laesning, ingen hydrering.

    Der er intet at slaa op: raekken ER afgjort, og det er hele dens pointe.
    Hydreringen findes for de AABNE, hvor svaret kan vaere givet et andet
    sted; her er svaret givet her. At hydrere alligevel ville betyde at
    spoerge ejeren om noget han allerede har svaret paa — og en utilgaengelig
    ejer ville faa en klaret post til at se foraeldet ud.

    Felterne er de SAMME som i ``feed()``, blot med ``klaret``/``udfald``
    tilfoejet, saa fladen kan bruge én post-type og kun skifte hvad den
    tilbyder af handlinger (intet).
    """
    del er_owner  # samme begrundelse som i aabne(): ikke et filter i dag
    ud: list[dict[str, Any]] = []
    for raekke in _lager.afsluttede(user_id, dage=dage):
        udfald = str(raekke["udfald"] or "")
        ud.append({
            "id": raekke["id"],
            "slags": raekke["slags"],
            "titel": raekke["titel"],
            "tekst": raekke["tekst"],
            "session_id": raekke["session_id"],
            "oprettet": raekke["oprettet"],
            "klaret": raekke["klaret"],
            "udfald": udfald,
            "udfald_tekst": _UDFALD_TEKST.get(udfald, "Klaret"),
            "kan_afgoere": False,
            "foraeldet": False,
        })
    return ud
