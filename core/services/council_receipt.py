"""Et raad kvitteres nu med det samme — Fase 6.

«start resolves on message acceptance, and send returns a message receipt
rather than a reply» og «parent can continue while an accepted continuable
child runs».

## Hvad det kostede at vente

Maalt 10/9-2026: 763 raads-runs, 17,4 sekunder i snit, 3,7 medlemmer pr. raad.
`convene_council` koerte runden SYNKRONT, saa Jarvis' tur froes indtil hele
raadet havde talt. Parallelisering bragte det fra ~64 til ~17 sekunder — men
sytten sekunders frys er stadig sytten sekunder hvor han ikke kan andet.

## Hvorfor kvitteringen ikke er en blindgyde

En kvittering uden afhentning er vaerre end at vente: saa er svaret vaek i
stedet for blot forsinket. Der er derfor TO veje tilbage til resultatet, og
begge fandtes i forvejen:

  `council_status(council_id)`   den direkte — `build_council_detail_surface`
  `recall_council_conclusions`   nettet — runden skriver sin konklusion til
                                 raads-hukommelsen naar den er faerdig
                                 (`agent_runtime_council` linje 636), OGSAA
                                 hvis ingen henter den

Glemmer han at hente, gaar deliberationen altsaa ikke tabt. Det er hele
grunden til at kvitteringen er forsvarlig her og ikke ville vaere det et sted
uden det net.
"""
from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# Kun for at kunne se i en test at traaden faktisk blev startet.
_STARTEDE: list[str] = []


def _nulstil_for_tests() -> None:
    _STARTEDE.clear()


def start_round_in_background(council_id: str) -> bool:
    """Start raadsrunden uden at vente paa den. Returnerer om den blev startet.

    Fejl i traaden SKAL kunne ses: en runde der doer stille efterlader et raad
    der ser ud til at vaere i gang for altid.
    """
    cid = str(council_id or "").strip()
    if not cid:
        return False

    def _koer() -> None:
        try:
            from core.services.agent_runtime import run_council_round
            run_council_round(cid)
        except Exception:
            logger.warning("raad %s: runden fejlede i baggrunden", cid,
                           exc_info=True)
            try:
                from core.services.child_failure_signal import note_child_ended
                note_child_ended(cid, status="failed",
                                 role="council",
                                 error="raadsrunden fejlede i baggrunden")
            except Exception:
                pass

    try:
        t = threading.Thread(target=_koer, name=f"council-{cid[:12]}",
                             daemon=True)
        t.start()
        _STARTEDE.append(cid)
        return True
    except Exception:
        logger.warning("raad %s: kunne ikke starte baggrunds-runden", cid,
                       exc_info=True)
        return False


def receipt(council_id: str, *, topic: str, roles: list[str],
            started: bool) -> dict[str, Any]:
    """Kvitteringen. Siger hvad der er ACCEPTERET — ikke hvad der blev svaret.

    Den fortaeller ogsaa HVORDAN man henter resultatet. En kvittering der ikke
    goer det, forudsaetter at laeseren kender huset.
    """
    return {
        "status": "accepted" if started else "error",
        "council_id": council_id,
        "topic": topic,
        "roles": list(roles or []),
        "member_count": len(roles or []),
        "accepted": bool(started),
        "hent_resultat": (
            f"Raadet er sat i gang og svarer ikke her. Hent det med "
            f"council_status(council_id='{council_id}') naar du er klar — "
            "eller senere med recall_council_conclusions, som ogsaa finder det "
            "hvis du glemmer at hente."
        ) if started else "Raadet kunne ikke startes.",
    }


def status(council_id: str) -> dict[str, Any]:
    """Hvor er raadet naaet til? Den direkte afhentning."""
    cid = str(council_id or "").strip()
    if not cid:
        return {"status": "error", "error": "council_id is required"}
    try:
        from core.services.agent_runtime_surfaces import (
            build_council_detail_surface,
        )
        flade = build_council_detail_surface(cid)
    except Exception as exc:
        return {"status": "error", "error": f"kunne ikke laese raadet: {exc}"}
    if not flade:
        return {"status": "error", "error": f"ukendt raad: {cid}"}
    return {"status": "ok", **flade}
