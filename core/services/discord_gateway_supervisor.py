"""Vagthund der genrejser Discord-gatewayen naar dens klienttraad er doed.

## Hvorfor filen findes (maalt 1-2/10-2026)

Den udgaaende Discord-kanal laa doed i ELLEVE TIMER uden at nogen saa det.
Journalen har hele kaeden:

    21:18:01  discord_gateway: started
    21:18:07  ERROR: discord_gateway: client error: 503 Service Unavailable
              upstream connect error ... reset reason: connection termination
    08:00:39  WARNING: cross-process send failed: runtime-http-503:
              {"detail":"gateway not owned by this process — refusing to forward"}

Gatewayen blev genetableret efter nattens genstart. Seks sekunder senere gav
DISCORDS egen infrastruktur en 503, og `_discord_thread_func` koerer klienten
én gang: fejler den, logges der og traaden doer. Der var ingen der startede den
igen, for `start_discord_gateway()` kaldes kun ved boot.

Konsekvensen var ikke en fejlmeddelelse nogen kunne se. Michelles morgenbrief
fyrede praecist kl. 07:30, kaldte `send_discord_dm` fire gange og fik 503 hver
gang; Mikkels morgenvejr fejlede identisk i samme sekund. Tasken virkede.
LEVERINGEN var vaek. Den slags skal ikke kunne staa stille en hel nat.

## Hvorfor en egen fil

`discord_gateway.py` er 1.784 linjer — allerede over husets 1.500-graense — og
en vagthund hoerer alligevel ikke sammen med det den vaager over: de traade der
doer, bor i det modul, og supervisoren skal overleve dem.

## Dette er et SIKKERHEDSNET, ikke rodaarsags-rettelsen

Rodaarsagen staar der stadig: `_discord_thread_func` koerer klienten ÉN gang og
har ingen genforbindelse. En selvhelbredelse fjerner symptomet og dermed
trangen til at finde fejlen — det kostede 13 dage sidst med `bash_session`, hvor
en respawn blev bygget i september og deadlocken i `close()` foerst blev fundet
senere. Saa: det rigtige naeste skridt er en genforbindelses-loekke i
`_run_client`, saa en forbigaaende 503 bliver et nyt forsoeg i stedet for en
doed traad. Supervisoren daekker det bredere tilfaelde — traaden doer af en
HVILKEN SOM HELST grund — og de to udelukker ikke hinanden.

## Hvorfor den ikke skjuler sin egen aarsag

En selvhelbredelse der tier goer skaden vaerre: saa forsvinder grunden til at
kanalen faldt, og man leder efter symptomet naeste gang. Derfor logger hver
reparation paa WARNING, og taelleren ligger i runtime_state_kv, saa «hvor mange
gange har den maattet rejse den i nat» er et tal man kan slaa op — ikke et
indtryk. Fyrer den gentagne gange, er det 503'en der skal undersoeges, ikke
vagthunden der skal skrues op.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime
from typing import Any, Final

logger = logging.getLogger(__name__)

#: Naar supervisoren tjekker foerste gang. Gatewayen forbandt historisk paa
#: 3-6 sekunder, saa 90 er rigeligt til at undgaa en reparation af noget der
#: stadig er ved at starte.
FOERSTE_TJEK_S: Final[float] = 90.0

#: Mellem to tjek naar alt er sundt. Et doedt kvarter er for laenge til en
#: kanal Bjoern faar morgenbriefs paa; et sekund ville hamre paa Discord.
TJEK_INTERVAL_S: Final[float] = 60.0

#: Loft paa ventetiden efter gentagne mislykkede forsoeg. Er Discord nede, er
#: det deres problem — vi skal ikke banke paa hvert minut i timevis.
BACKOFF_MAKS_S: Final[float] = 600.0

#: Hvor laenge vi venter paa at de gamle traade faktisk doer. `stop_` saetter
#: kun flag; traadene opdager dem foerst ved naeste gennemloeb.
STOP_VENT_S: Final[float] = 10.0

#: Hvor laenge klienten maa bruge paa at forbinde foer vi kalder forsoeget
#: mislykket. Den historiske forbindelsestid er 3-6 s.
EJERSKAB_GRACE_S: Final[float] = 20.0

#: Egen noegle — `discord_gateway.status` ejes af gatewayen selv.
TILSTAND_KV_NOEGLE: Final[str] = "discord_gateway.supervisor"

_traad: threading.Thread | None = None
_koerer = False
_reparationer = 0


def _gateway_er_ejet() -> bool:
    """Ejer DENNE proces gatewayen? Fejl regnes som «ja», saa en laesefejl
    aldrig kan udloese en reparation af noget der maaske var sundt."""
    try:
        from core.services.discord_gateway import _is_gateway_owner
        return bool(_is_gateway_owner())
    except Exception as exc:
        logger.warning(
            "discord_supervisor: kunne ikke laese ejerskab (%s) — "
            "antager sundt og venter", exc,
        )
        return True


def _discord_er_slaaet_til() -> bool:
    """Er Discord konfigureret OG aktiveret? Ellers skal vi ikke rejse noget."""
    try:
        from core.services.discord_config import load_discord_config
        config = load_discord_config()
    except Exception as exc:
        logger.warning("discord_supervisor: kunne ikke laese config: %s", exc)
        return False
    return bool(config) and bool(config.get("enabled", True))


def _skriv_tilstand(**felter: Any) -> None:
    """Spejl supervisorens tilstand saa Centralen kan se den."""
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(TILSTAND_KV_NOEGLE, {
            "reparationer": _reparationer,
            "opdateret_at": datetime.now(UTC).isoformat(),
            **felter,
        })
    except Exception as exc:
        logger.debug("discord_supervisor: kunne ikke skrive tilstand: %s", exc)


def _vent_paa_at_traadene_doer() -> bool:
    """Vent indtil klient- og subscriber-traaden er vaek. True hvis de doede.

    Uden dette rammer vi fælden i `start_discord_gateway()`: den returnerer
    «already running» hvis klient- ELLER subscriber-traaden lever, mens
    ejerskabet kun maaler klienttraaden. Doer klienten alene, ville et nyt
    kald derfor aldrig reparere noget — det ville melde «already running» for
    evigt, mens ejerskabet stod False.
    """
    frist = time.monotonic() + STOP_VENT_S
    while time.monotonic() < frist:
        try:
            from core.services import discord_gateway as dg
            klient = dg._thread
            sub = dg._sub_thread
        except Exception as exc:
            logger.warning("discord_supervisor: kunne ikke laese traade: %s", exc)
            return False
        klient_doed = klient is None or not klient.is_alive()
        sub_doed = sub is None or not sub.is_alive()
        if klient_doed and sub_doed:
            return True
        time.sleep(0.5)
    logger.warning(
        "discord_supervisor: traadene levede stadig efter %.0fs — "
        "springer dette forsoeg over", STOP_VENT_S,
    )
    return False


def _reparer() -> bool:
    """Stop resterne og start gatewayen forfra. True hvis ejerskab blev vundet."""
    global _reparationer
    _reparationer += 1
    logger.warning(
        "discord_supervisor: gatewayen er IKKE ejet af denne proces — "
        "forsoeger at rejse den (reparation nr. %s)", _reparationer,
    )
    _skriv_tilstand(sidste_forsoeg_at=datetime.now(UTC).isoformat(),
                    sidste_resultat="i gang")
    try:
        from core.services.discord_gateway import (
            start_discord_gateway,
            stop_discord_gateway,
        )
    except Exception as exc:
        logger.error("discord_supervisor: kunne ikke importere gatewayen: %s", exc)
        _skriv_tilstand(sidste_resultat="import-fejlede", sidste_fejl=str(exc)[:200])
        return False

    try:
        stop_discord_gateway()
    except Exception as exc:
        logger.warning("discord_supervisor: stop fejlede (fortsaetter): %s", exc)

    if not _vent_paa_at_traadene_doer():
        _skriv_tilstand(sidste_resultat="traade-doede-ikke")
        return False

    try:
        start_discord_gateway()
    except Exception as exc:
        logger.error("discord_supervisor: start fejlede: %s", exc)
        _skriv_tilstand(sidste_resultat="start-fejlede", sidste_fejl=str(exc)[:200])
        return False

    frist = time.monotonic() + EJERSKAB_GRACE_S
    while time.monotonic() < frist:
        if _gateway_er_ejet():
            logger.info(
                "discord_supervisor: gatewayen er rejst igen "
                "(reparation nr. %s)", _reparationer,
            )
            _skriv_tilstand(sidste_resultat="rejst")
            return True
        time.sleep(1.0)

    logger.error(
        "discord_supervisor: gatewayen blev ikke ejet inden %.0fs — "
        "Discord afviser sandsynligvis forbindelsen", EJERSKAB_GRACE_S,
    )
    _skriv_tilstand(sidste_resultat="intet-ejerskab-efter-start")
    return False


def _loop() -> None:
    """Tjek med faste mellemrum; bak eksponentielt ud naar reparation fejler."""
    _sov(FOERSTE_TJEK_S)
    ventetid = TJEK_INTERVAL_S
    while _koerer:
        if not _discord_er_slaaet_til():
            _sov(TJEK_INTERVAL_S)
            continue
        if _gateway_er_ejet():
            ventetid = TJEK_INTERVAL_S
            _sov(ventetid)
            continue
        if _reparer():
            ventetid = TJEK_INTERVAL_S
        else:
            ventetid = min(ventetid * 2, BACKOFF_MAKS_S)
            logger.warning(
                "discord_supervisor: venter %.0fs foer naeste forsoeg", ventetid,
            )
        _sov(ventetid)
    logger.info("discord_supervisor: stoppet")


def _sov(sekunder: float) -> None:
    """Sov i smaa bidder, saa et stop ikke skal vente et helt interval."""
    for _ in range(int(sekunder * 2)):
        if not _koerer:
            return
        time.sleep(0.5)


def start_discord_gateway_supervisor() -> None:
    """Start vagthunden. Sikker at kalde ubetinget."""
    global _traad, _koerer
    if _traad is not None and _traad.is_alive():
        logger.info("discord_supervisor: koerer allerede")
        return
    if not _discord_er_slaaet_til():
        logger.info("discord_supervisor: Discord er ikke slaaet til — starter ikke")
        return
    _koerer = True
    _traad = threading.Thread(target=_loop, daemon=True, name="discord-supervisor")
    _traad.start()
    logger.info(
        "discord_supervisor: startet (foerste tjek om %.0fs, derefter hvert %.0fs)",
        FOERSTE_TJEK_S, TJEK_INTERVAL_S,
    )


def stop_discord_gateway_supervisor() -> None:
    """Stop vagthunden. SKAL kaldes FOER `stop_discord_gateway()` ved nedlukning,
    ellers rejser supervisoren gatewayen igen midt i en afslutning."""
    global _koerer
    _koerer = False


def supervisor_status() -> dict[str, Any]:
    """Til Centralen: koerer vagthunden, og hvor mange gange har den maattet
    rejse gatewayen i denne proces' levetid?"""
    return {
        "koerer": _traad is not None and _traad.is_alive(),
        "reparationer": _reparationer,
        "tjek_interval_s": TJEK_INTERVAL_S,
    }
