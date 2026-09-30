"""Afgoer hvad et agentisk segment blev til, og goer det durabelt.

Udskilt fra `visible_runs` (Boy Scout-reglen: filen er paa 7.542 linjer).
Enheden er sammenhaengende: den retter exit-grunden saa den ikke lyver, laeser
hvor langt genoptagelses-kaeden er naaet, og lader
`visible_run_segment_settlement` skrive posten og faelde dommen. Kalderen faar
dommen tilbage og staar selv for SSE og tilstands-markering — det kan ikke
flyttes med, fordi det er en generator.

## Hvorfor taelleren har sin egen fejl-retning

Loftet i `visible_terminal_policy` er `recovery_attempt >= recovery_limit`.
Fejler opslaget af kaeden, er der to muligheder, og de er ikke lige gode:

* **0** — «det her er foerste forsoeg». Saa fortsaetter turen, og fejler
  opslaget hver gang, fortsaetter den for evigt. Det var koden indtil 30/9-2026,
  og den variant koster penge og fylder skaermen uden at nogen kan se hvorfor.
* **Loftet** — «kaeden er opbrugt». Saa standser turen med et aerligt varsel om
  at checkpointet er bevaret, og mennesket kan sige fortsaet.

Den anden er til at komme sig over; den foerste er ikke. Derfor standser vi naar
vi ikke kan taelle — og skriver hvorfor i loggen, saa et opslag der fejler
systematisk ikke ligner en almindelig afslutning.
"""
from __future__ import annotations

import logging

from core.services.visible_run_segment_settlement import (
    SegmentUdfald,
    settle_segment_exit,
)

logger = logging.getLogger(__name__)

#: Hvor mange gange en tur maa genoptages i traek.
#:
#: Tallet staar her og sendes MED til afregningen, i stedet for at lade
#: `settle_segment_exit` bruge sin egen standard. Ellers kunne fallbacken
#: nedenfor og loftet drive fra hinanden, og saa ville «vi kan ikke taelle»
#: holde op med at betyde «stop». Det kan ikke importeres fra
#: `auto_continuation.MAKS_KAEDE`, for det er praecis den import der kan fejle.
GENOPTAGELSES_LOFT = 3


def kaede_nr_eller_loft(session_id: str) -> int:
    """Hvor langt er genoptagelses-kaeden naaet for denne samtale?

    Kan den ikke laeses, gives loftet tilbage — se modulets docstring.
    """
    try:
        from core.services.auto_continuation import kaede_nr
        return max(0, int(kaede_nr(session_id)))
    except Exception:
        logger.warning(
            "kunne ikke laese genoptagelses-kaeden for session %s — segmentet "
            "afregnes som opbrugt frem for at fortsaette i blinde",
            session_id, exc_info=True)
        return GENOPTAGELSES_LOFT


def afgoer_segment_udfald(
    *,
    run_id: str,
    session_id: str,
    exit_reason: str,
    final_text: str = "",
    finish_reason: str = "",
    forced_finalize: bool = False,
    pending_tool_intent: bool = False,
    truncated: bool = False,
) -> SegmentUdfald:
    """Skriv segmentets ophoer durabelt og giv dommen tilbage.

    `truncated` er en runde der blev afkortet (`finish_reason=length`). Sluttede
    loekken samtidig «completed», lyver det ordet om ren succes: der ER et svar,
    men det blev klippet. Grunden rettes derfor foer afregningen, saa telemetri
    og incident ser det aerligt. (2026-08-19.)
    """
    grund = str(exit_reason or "")
    if truncated and grund == "completed":
        grund = "completed-truncated"
    return settle_segment_exit(
        run_id=run_id,
        session_id=session_id,
        exit_reason=grund,
        final_text=final_text,
        finish_reason=finish_reason,
        forced_finalize=forced_finalize,
        pending_tool_intent=pending_tool_intent,
        recovery_attempt=kaede_nr_eller_loft(session_id),
        recovery_limit=GENOPTAGELSES_LOFT,
        summary=grund,
    )
