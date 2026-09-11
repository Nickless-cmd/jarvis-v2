"""Lukker processen ned? Ét sted der ejer svaret.

Bjørn/Jarvis målte 11/9-2026 hvad det koster at ingen kan spørge:

    13:27:11  Shutting down — turen står i runde 3
    13:27:41  ERROR: Cancel 1 running task(s), timeout graceful shutdown exceeded
    13:27:43  ny proces klar

Mellem de to linjer kørte turen runde 3 → 10. Syv runder, fjorten bash-kald,
udført EFTER shutdown-signalet og derefter smidt væk.

Årsagen var ikke at løkken ignorerede signalet. Det var at signalet aldrig nåede
frem: et `grep` efter `shutting_down|_SHUTDOWN|is_shutting_down|shutdown_event`
i hele `core/` og `apps/api/` gav ÉN forekomst — eventbussens writer-timeout.
Der fandtes intet flag at spørge om.

`--timeout-graceful-shutdown 30` er derfor sandt om hensigten («giv arbejdet tid
til at blive færdigt») og forkert om hvad der sker. De 30 sekunder er spild frem
for udsættelse, og at sænke dem taber de samme runder — bare hurtigere.

## Hvorfor et flag og ikke en exception

Arbejde der opdager nedlukning skal kunne afslutte PÆNT — gemme det den har,
skrive sin status, og returnere. En exception midt i en runde ville efterlade
præcis den halvfærdige tilstand vi prøver at undgå. Derfor: et flag man spørger
om ved en naturlig grænse, ikke noget der rives ud af hænderne på nogen.

## Tre tilstande findes ikke her

`lukker_ned()` er True eller False, aldrig None — i modsætning til
`turen_koerer_stadig()` og `lever()`. Det er ikke en måling af noget udefra;
det er vores egen tilstand, og den kender vi altid.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_laas = threading.Lock()
_lukker = False
_grund = ""


def markér_nedlukning(grund: str = "") -> None:
    """Sig at processen er på vej ned. Idempotent."""
    global _lukker, _grund
    with _laas:
        if _lukker:
            return
        _lukker = True
        _grund = str(grund or "shutdown")
    logger.info("proces markeret til nedlukning: %s", _grund or "shutdown")


def lukker_ned() -> bool:
    """Er processen på vej ned? Spørg ved en naturlig grænse, ikke midt i noget."""
    with _laas:
        return _lukker


def grund() -> str:
    with _laas:
        return _grund


def installer_signalvagt() -> None:
    """Sæt flaget når SIGNALET ankommer — ikke når lifespan når sin shutdown.

    Målt 11/9-2026 med tre offer-ture der blev kappet med vilje:

        08:25:11  Waiting for application shutdown.
        08:25:13  visible-run unhandled exception: chat session not found
        08:25:13  proces markeret til nedlukning: lifespan-shutdown

    Lifespan-shutdown kører SIDST i uvicorns nedlukning — efter at
    forbindelserne er revet ned. Flaget blev altså sat i samme sekund som
    runnet døde, og løkken nåede aldrig en rundegrænse hvor den kunne spørge.
    Tre kappede ture, nul fyringer af vagten.

    Det var ikke vagten der var forkert. Det var HVORNÅR nogen fortalte den at
    vi lukkede. En vagt der får besked sidst er en vagt der aldrig kan nå at
    sige fra.

    uvicorn installerer sine egne handlers i `capture_signals()` FØR lifespan
    starter (`serve()` wrapper `_serve()` i den context manager), så vi kan
    lægge os udenom dem og kalde videre. Vi ERSTATTER dem aldrig: uden
    videresendelse ville processen ikke lukke ned overhovedet.
    """
    import signal

    for _sig in (signal.SIGTERM, signal.SIGINT):
        try:
            _forrige = signal.getsignal(_sig)
        except Exception:
            continue

        def _vagt(signum, frame, _f=_forrige):  # noqa: ANN001
            try:
                markér_nedlukning(f"signal-{signum}")
            except Exception:
                pass
            if callable(_f):
                _f(signum, frame)

        try:
            signal.signal(_sig, _vagt)
        except Exception:
            # Kun hovedtråden må lytte på signaler. Kan vi ikke, falder vi
            # tilbage på lifespan-hooken — sent, men ikke ingenting.
            logger.debug("kunne ikke installere signalvagt for %s", _sig, exc_info=True)


def nulstil_til_test() -> None:
    """Kun til tests — en proces vender ikke tilbage fra nedlukning."""
    global _lukker, _grund
    with _laas:
        _lukker = False
        _grund = ""
