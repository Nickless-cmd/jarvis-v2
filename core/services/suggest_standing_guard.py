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

## Spoergsmaalet hoerer ogsaa her (Bjorn 11/10-2026)

Vagten taeller nu BAADE `suggest_next_task` og `pause_and_ask` som stilling
taget. Foer denne dato gjaldt kun den foerste — saa naar Jarvis havde et
spoergsmaal, skubbede vagten ham mod komponisten, og spoergsmaalet endte i
Bjorns skrivefelt som om det var hans egen besked. Et spoergsmaal ER en
stillingtagen: turen sluttede med et spoergsmaal, ikke med et svar der mangler
et naeste skridt. Noten maa derfor ikke fyre naar spoergsmaalet er stillet.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Iterable

logger = logging.getLogger(__name__)

_ENV = "JARVIS_SUGGEST_STANDING_GUARD"

#: Værktøjerne der TAGER stilling til næste skridt. Er ét af dem kaldt, er
#: stillingen taget, og noten maa ikke fyre.
#:
#: `suggest_next_task` peger paa næste TRÆK i Bjorns ord; `pause_and_ask`
#: stiller spoergsmaalet til ham og afslutter turen (Bjorn 11/10-2026:
#: «spoergsmaal skal gaa til pause and ask»). Foer denne dato talte kun den
#: foerste som stillingtagen — saa naar Jarvis havde et spoergsmaal, skubbede
#: vagten ham mod komponisten i stedet, og spoergsmaalet endte i Bjorns
#: skrivefelt som om det var hans egen besked.
STILLING_TOOL_NAMES: tuple[str, ...] = ("suggest_next_task", "pause_and_ask")

#: Bagudkompatibelt navn — kaldestedet og testene bruger det gamle navn.
SUGGEST_TOOL_NAMES: tuple[str, ...] = STILLING_TOOL_NAMES


def suggest_standing_guard_enabled() -> bool:
    """Default FALSE (Bjørn 19/10-2026). Env kan tænde den igen.

    ## Hvorfor standarden blev vendt

    Vagten gør noget dyrere end den ser ud: når den fyrer, skriver den en note
    i halen og kalder ``continue`` — altså **starter en ekstra runde** efter den
    runde hvor svaret allerede var skrevet. Målt 19/10-2026: ``done`` (og dermed
    ``final_answer_start``, og dermed folden i chat mode) falder først når
    løkken ikke har flere værktøjskald. Så hver ekstra runde skubber folden, og
    slutsvaret skal flytte sig ud af et hoved der allerede er klappet sammen,
    midt i at det streamer. Det er «teleporteringen» Bjørn beskrev.

    Reglen den skulle flytte ned («tag stilling til næste skridt») står nu som
    en fast linje i ``output_discipline`` — med den tilføjelse at kaldet skal
    ligge FØR den afsluttende tekst, ikke efter. En regel i prompten koster
    ingen ekstra runde.

    Målt før omlægningen: 59 kald af ``suggest_next_task`` den 19/10 alene. Der
    er altså ingen tegn på at feltet står tomt uden vagten — den antagelse kom
    fra 7/10, hvor Jarvis var eneste kilde og værktøjet var nyt.

    Env vinder, så den kan tændes igen uden genstart. Enhver tvivl → FRA: en
    vagt der genstarter turen skal kunne slås fra af den der mærker prisen.
    """
    try:
        raw = str(os.environ.get(_ENV) or "").strip()
    except Exception:  # miljøet kan ikke læses → standarden (fra) gælder
        return False
    if not raw:
        return False
    return raw.lower() in {"1", "true", "yes", "on"}


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
    * `suggest_next_task` eller `pause_and_ask` kaldt — stillingen ER taget.
      Noten ville være en gentagelse. Et spoergsmaal stiller turen lige saa
      afsluttet som et forslag goer.
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
        if any(n in STILLING_TOOL_NAMES for n in navne):
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
        "dansk. Skal BJØRN derimod beslutte noget, kald `pause_and_ask` — et "
        "spørgsmål hører ikke i komponisten, og den anbefalede mulighed står "
        "først med «(anbefalet)» i teksten. Er tråden færdig, afslut uden at "
        "gentage dig."
    )
