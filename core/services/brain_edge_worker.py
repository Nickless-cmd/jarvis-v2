"""Kant-udledningen for en ny hjerne-post flyttes ud af værktøjets ventetid.

## Hvad der blev målt (17/9-2026)

Bjørn: «hans remember_this tool er historisk langsomt». Målt på ct105:

* 9.705 aktive poster med embedding er kandidater — hver enkelt gang.
* For hver kandidat læses dens markdown-fil fra disken og entity-overlappet
  regnes ud: **~12 sekunder** pr. `remember_this`.
* Selve skrivningen af posten er derimod hurtig, og embeddingen af den nye
  post tog 0,20 s.

Så det er ikke skrivningen der er langsom. Det er en O(alle poster)-udledning
der står i vejen for et svar.

## Hvorfor ikke bare afgrænse kandidaterne

Det var det første jeg prøvede, og målingen sagde nej. Tærsklen er 0,4 og
formlen `0,4·t + 0,4·s + 0,2·e + 0,15·kæde`. Entity og kæde kan tilsammen give
0,35 — næsten hele tærsklen — så en kandidat kan i princippet klare sig på dem
alene. Den eksakte øvre grænse udelukkede **0 af 9.705**. En afgrænsning her
ville altså ikke være en optimering, men en ændring af hvilke kanter der
findes, og den beslutning hører ikke hjemme i en fejlretning af ventetid.

## Hvorfor det er sikkert at gøre det bagefter

`jarvis_brain_daemon.b4_catchup_infer_once` kører hver time og finder præcis
poster UDEN kanter — dens egen docstring nævner `skip_temporal=True` som den
situation den er lavet til. Går processen ned inden tråden er færdig, samles
posten altså op af sig selv. Derfor er baggrunden ikke et løfte vi selv skal
holde.

## Hvorfor én kø og ikke en tråd pr. post

To udledninger på samme tid er to gange 9.705 filer og to skrivere på samme
sqlite-indeks. Køen gør arbejdet seriellt: samme samlede tid, ingen
låsekonkurrence, og ét sted at se hvor meget der venter.
"""
from __future__ import annotations

import logging
import queue
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

#: Nok til en menneskelig byge af noter. Løber den fuld, springes udledningen
#: over — og time-passet tager posten. Bedre end at blokere værktøjet, som er
#: netop det vi er her for at undgå.
MAKS_KOE: int = 200

_koe: queue.Queue[tuple[str, datetime | None]] = queue.Queue(maxsize=MAKS_KOE)
_traad: threading.Thread | None = None
_laas = threading.Lock()


def _arbejd() -> None:
    while True:
        entry_id, now = _koe.get()
        try:
            from core.services.jarvis_brain import infer_temporal_edges
            antal = infer_temporal_edges(entry_id, now=now)
            logger.info("brain-kanter: %s fik %d kanter", entry_id, antal)
        except Exception:
            # Time-passet tager den. En tabt udledning er en forsinkelse,
            # ikke et tab.
            logger.warning("brain-kanter: udledning fejlede for %s", entry_id,
                           exc_info=True)
        finally:
            _koe.task_done()


def koesaet(entry_id: str, now: datetime | None = None) -> bool:
    """Læg en post i kø til kant-udledning. `False` = køen er fuld.

    Kaster aldrig: en note der er skrevet, må ikke fejle på sit efterarbejde.
    """
    if not entry_id:
        return False
    global _traad
    try:
        with _laas:
            if _traad is None or not _traad.is_alive():
                _traad = threading.Thread(target=_arbejd, name="brain-edge-worker",
                                          daemon=True)
                _traad.start()
        _koe.put_nowait((str(entry_id), now))
        return True
    except queue.Full:
        logger.warning("brain-kanter: koeen er fuld — %s tages af time-passet",
                       entry_id)
        return False
    except Exception:
        logger.warning("brain-kanter: kunne ikke koesaette %s", entry_id,
                       exc_info=True)
        return False


def venter() -> int:
    """Hvor mange poster der står i kø. Til test og til at se hvor langt bagud."""
    return _koe.qsize()
