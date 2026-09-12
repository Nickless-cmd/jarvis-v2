"""Fejeren for udløbne godkendelser — den kalder `expire_stale()`.

## Hvorfor den findes

`db_approval_bridge.expire_stale()` har eksisteret og været testet siden broen
blev bygget, og har haft **nul produktionskaldere**. Målt 12/9-2026 på
runtime-databasen kostede det fem poster der stod som `pending` for evigt, de
ældste 36 timer over deres udløb — alle på den samme session, og deres `run_id`
fandtes ikke længere i `agent_runs`.

De faldt mellem to mekanismer: fejeren blev aldrig kaldt, og opgiveren
(`abandon_run`) ser kun runs der stadig findes. Søsteren fik sin kalder da
`visible_run_abandonment` blev bygget — og dens egen docstring siger hvorfor det
betød noget: *«Broen kunne skelne fra dag ét, men ingen kaldte `abandon()`. En
skelnen der aldrig foretages er ikke en skelnen.»* Den rettelse tjekkede ikke
naboen.

## Hvad den rører, og hvad den aldrig rører

`expire_stale()` markerer kun `pending`, `approved` og `prepared` hvis udløbet
er passeret. Den rører **aldrig** `dispatching`: en afsendelse der er i gang
udløber ikke, fordi dens udfald stadig er ukendt. Den regel ligger i broen, ikke
her — denne fil beslutter kun HVORNÅR der fejes, aldrig HVAD.

## Kadencen

Fem minutter. Godkendelser lever en time (`DEFAULT_TTL_S`), så det er rigeligt
til at en udløbet post ikke ligger og ser uafklaret ud, og sjældent nok til at
en tom fejning ikke koster en skrivetransaktion hvert andet minut. Familien
kalder hvert tick; drosling sker her, som hos `cache_maintenance` og
`signal_decay`.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_CADENCE_MINUTES = 5

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}


def _nulstil_for_tests() -> None:
    global _last_tick_at, _last_result
    _last_tick_at = None
    _last_result = {}


def tick_approval_expiry_daemon(now: datetime | None = None) -> dict[str, object]:
    """Fej udløbne godkendelser hvis kadencen er gået. Selv-sikker.

    `now` er injicerbar, så kadencen kan prøves uden at vente fem minutter —
    en test der skal sove for at måle noget, bliver ikke kørt.
    """
    global _last_tick_at, _last_result

    nu = now or datetime.now(UTC)

    if _last_tick_at is not None and (nu - _last_tick_at) < timedelta(minutes=_CADENCE_MINUTES):
        return {"fejet": False, "grund": "kadence"}

    try:
        from core.runtime.db_approval_bridge import expire_stale
        antal = int(expire_stale(now=nu))
    except Exception as exc:
        # Familien isolerer allerede fejl, men en fejer der stille holder op
        # med at virke er praecis den fejl denne fil blev skrevet for at rette.
        logger.warning("approval_expiry: kunne ikke feje: %s", exc, exc_info=True)
        _last_tick_at = nu
        _last_result = {"fejet": False, "grund": "fejl", "fejl": str(exc)[:200]}
        return dict(_last_result)

    _last_tick_at = nu
    _last_result = {"fejet": True, "udloebet": antal}

    if antal:
        # SIG DET HOEJT. En post der gaar fra «venter» til «udloebet» er en
        # godkendelse ingen naaede at svare paa, og det er vaerd at vide at der
        # var noget at feje — ellers ser en sund fejer og en doed fejer ens ud.
        logger.info("approval_expiry: markerede %d udloebet godkendelse(r)", antal)
        try:
            from core.eventbus.bus import event_bus
            # "approvals" i FLERTAL: det er den familie der findes i
            # ALLOWED_EVENT_FAMILIES. Foerste udgave brugte ental, og publish()
            # kaster paa en ukendt familie - hvorefter except nedenfor slugte
            # det. Haendelsen var altsaa aldrig blevet udsendt.
            event_bus.publish("approvals.expired", {"count": antal,
                                                    "at": nu.isoformat()})
        except Exception:
            logger.debug("approval_expiry: kunne ikke publicere hændelsen", exc_info=True)

    return dict(_last_result)


def sidste_resultat() -> dict[str, object]:
    """Hvad fejeren sidst udrettede — så en læser kan se om den kører."""
    return dict(_last_result)
