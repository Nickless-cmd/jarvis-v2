"""Stillingtagen til næste skridt ved tur-afslutning (Bjørn 7/10-2026).

## Hvad der var galt

Instruktionen fandtes allerede. `output_discipline` beder om den:

    Before you finish a turn that leaves a next step, call suggest_next_task …

Men den er én linje blandt tyve, langt oppe i prompten, og den druknede.
Målt mod `composer_choices`: siden 28/9-2026 — hvor den lokale model blev
droppet og Jarvis blev ENESTE kilde — faldt forslag oprettet pr. dag fra 20-85
til typisk under 10. Den 7/10: fire. Feltet står altså næsten altid tomt.

Problemet er ikke at værktøjet mangler. Det er at reglen ligger det forkerte
sted: i den generelle disciplin frem for i BESLUTNINGSØJEBLIKKET. Vagten her
flytter den samme regel ned til det punkt hvor den skal bruges — ved
tur-afslutning.

## Hvorfor en BETINGELSE og ikke et krav

Formen er Bjørns: «få dig til at tage stilling … som det sidste i hver tur».

Ordene er valgt med vilje. En note der sagde «kald suggest_next_task» ville
gøre værktøjet til en tvang og fylde komponisten med forslag der ikke er
rigtigt arbejde — og værktøjets egen regel («spring over når tråden er færdig»)
ville blive slidt ned. En note der siger «tag stilling» gør det modsatte:
«nej, der er intet næste skridt» er et gyldigt svar.

Og noten fyrer ikke på hver tur. Den kræver at turen faktisk UDFØRTE arbejde —
kaldte mindst ét værktøj — og at der ikke allerede ligger et forslag.

## Hvad noten ser ud

Den går i `_vaerns_advarsler` (og halen), altså i `_exchange_text()` — den
del der bliver næste rundes model-input. Den rører ALDRIG `_a_parts`, så Bjørn
ser den ikke. Det er den usynlige kanal, samme som `tomt_loefte_advarsel`.

## Loftet

ÉN gang pr. tur. En gate der altid siger «bliv ved» må ikke kunne holde turen
i live for evigt — samme grund som `_stop_hook_resumed` og baggrunds-shell-
genoptagelsen har hvert sit loft.

## Fail-retningen

Kan noget ikke afgøres, fyrer vagten ikke. En vagt der kaster ville vælte
hver tur den rører; en vagt der fyrer på et gæt ville fylde komponisten med
støj. Begge er værre end at tie.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterable

logger = logging.getLogger(__name__)

_ENV = "JARVIS_SUGGEST_STANDING_GUARD"

#: Værktøjet der LÆGGER forslaget. Er det kaldt, er stillingen taget.
SUGGEST_TOOL_NAMES: tuple[str, ...] = ("suggest_next_task",)


def suggest_standing_guard_enabled() -> bool:
    """Default TRUE (Bjørn bad om den 7/10-2026). Env vinder, så den kan slås
    fra uden genstart. Enhver tvivl → til."""
    try:
        raw = str(os.environ.get(_ENV) or "").strip()
    except Exception:  # miljøet kan ikke læses → standarden (til) gælder
        return True
    if not raw:
        return True
    return raw.lower() not in {"0", "false", "no", "off"}


def mangler_stilling(
    *,
    called_tool_names: Iterable[str] | None,
    nudged_already: bool = False,
    final_text: str = "",
    is_last_round: bool = False,
    er_autonom: bool = False,
) -> bool:
    """True når turen udførte arbejde og intet forslag blev lagt.

    Ren funktion — ingen I/O, ingen tilstand. Kaster aldrig: enhver fejl → False
    (normal afslutning, præcis som før vagten fandtes).

    Betingelserne, og hvorfor hver enkelt er der:

    * `nudged_already` — loftet. Én stillingtagen pr. tur.
    * `er_autonom` — et autonomt nat-run har ingen bruger til stede. Forslaget
      hører til en samtale med Bjørn; i en nat-session ville det koste en runde
      pr. nat uden at nogen kunne se forslaget. `run.autonomous` er præcis det
      flag (`True = heartbeat-triggered, no user present`).
    * `is_last_round` — på den tvungne afslutningsrunde er der ingen runde
      tilbage at svare i; noten ville være en død besked. Samme gate som
      `skill_gate_guard`.
    * tom `final_text` — der er intet svar at tage stilling EFTER. Tom
      completion er en anden vagts sag.
    * ingen kaldte værktøjer — turen udførte intet arbejde, så der er intet
      næste skridt at pege på. En ren samtale-tur får ikke noten.
    * `suggest_next_task` kaldt — stillingen ER taget. Noten ville være en
      gentagelse.
    """
    try:
        if nudged_already:
            return False
        if er_autonom:
            return False
        if is_last_round:
            return False
        if not str(final_text or "").strip():
            return False
        navne = [str(n).strip() for n in (called_tool_names or []) if str(n).strip()]
        if not navne:
            return False
        if any(n in SUGGEST_TOOL_NAMES for n in navne):
            return False
        return True
    except Exception:
        logger.debug("mangler_stilling fejlede", exc_info=True)
        return False


def build_nudge() -> str:
    """Beskeden der lægges i turen. Bedømmer, opfordrer ikke til gentagelse."""
    from core.services.visible_run_guard_notices import SYSTEM_MAERKE

    return (
        f"\n\n{SYSTEM_MAERKE}\n"
        "Turen udførte arbejde og er ved at slutte, men der ligger intet forslag "
        "i Bjørns komponist. Dette er ikke en anmodning om at gentage dit svar. "
        "Tag stilling i ÉN handling: er der et næste skridt, kald "
        "`suggest_next_task` med det i Bjørns ord — én linje, højst ti ord, "
        "dansk. Er tråden færdig, afslut uden at gentage dig."
    )
