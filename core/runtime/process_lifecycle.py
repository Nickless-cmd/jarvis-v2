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


def nulstil_til_test() -> None:
    """Kun til tests — en proces vender ikke tilbage fra nedlukning."""
    global _lukker, _grund
    with _laas:
        _lukker = False
        _grund = ""
