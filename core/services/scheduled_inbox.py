"""En fyret `schedule_task` skal efterlade en varig række i indbakken.

Bjørn 10/10-2026: «så skal vi sørge for dit reminder tool faktisk når din
inbox.»

## Hullet (målt 10/10-2026)

`schedule_task` skriver til `scheduled_tasks` og fyrer via nudge →
initiativkø → autonomt run. Den rører ALDRIG `inbox_items`. Indbakken viste
opgaven som «PÅ VEJ» — men laest fra `scheduled_tasks`-tabellen, ikke fra en
durabel post. I samme øjeblik opgaven fyrede, forsvandt den fra visningen, og
der fandtes intet spor af at noget var lovet og indfriet.

Det er samme fejlform som `self_wakeup` havde før 4/10: kæden virker
upåklageligt på nul rækker.

## Hvorfor ved FYRINGEN og ikke ved bookingen

En planlagt opgave er ikke en forpligtelse mens den venter — den er en aftale
om et tidspunkt. Posten bliver aktuel i det øjeblik den fyrer. Registrerede vi
ved bookingen, ville indbakken fyldes af «PÅ VEJ»-poster der endnu ikke har
gjort noget, og `planlagte_vaekning_ids`-mønstret (posten venter ikke på nogen
mens den er pending) ville skulle genopfindes her.

## Hvorfor `scheduled` ikke gater

En planlagt opgave er husets, ikke en forpligtelse: den må oprette, aldrig
nægte en mutation. Kildetypen står derfor i `IKKE_GATENDE_KILDETYPER`, og
`registrer_kilde` sætter `kraever_handling=False` af sig selv.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def registrer_fyret_opgave(
    *, bruger_id: str, task_id: str, focus: str,
) -> dict[str, Any]:
    """Skriv en durabel indbakke-post for en netop fyret planlagt opgave.

    Idempotent per (bruger, `scheduled`, task_id): polleren kan ramme den to
    gange, og `opret_eller_hent` returnerer da den eksisterende række urørt.

    Self-safe: en fejlet skrivning må ALDRIG forhindre at opgaven fyrer. Den
    returnerer `status="fejl"` og lader kalderen fortsætte — men fejlen logges,
    for en forpligtelse uden sin post er usynlig.
    """
    bruger_id = str(bruger_id or "").strip()
    task_id = str(task_id or "").strip()
    if not bruger_id or not task_id:
        return {"status": "fejl", "error": "bruger_id og task_id kraeves"}
    try:
        from core.services.inbox_state import registrer_kilde

        r = registrer_kilde(
            bruger_id=bruger_id,
            kildetype="scheduled",
            kilde_id=task_id,
            beskrivelse=str(focus or "")[:200],
        )
        if r.get("status") != "ok":
            logger.warning(
                "scheduled_inbox: %s blev IKKE registreret i indbakken: %s",
                task_id, r.get("error"))
        return r
    except Exception as exc:  # noqa: BLE001
        # Opgaven ER fyret. En fejl her må ikke rulle den tilbage — men den må
        # heller ikke være tavs, for så står en indfriet aftale uden sit spor.
        logger.warning("scheduled_inbox: kunne ikke registrere %s: %s", task_id, exc)
        return {"status": "fejl", "error": str(exc)}
