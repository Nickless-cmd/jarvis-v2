"""Ret en ødelagt ``jarvis-ui``-blok FØR svaret vises — ikke efter.

Baggrund (målt 25/10-2026, Bjørn): «disse fejler stadig … kan vi ikke sørge
for hvis formatet ikke er korrekt, afvises den inden den vises og du kan
korrigere og lave den der virker? istedet for runden skal slutte og så skal
jeg bede dig lave en ny … det er præcis sådan nogen fejl en bruger ikke må
opleve.»

Han har ret i rækkefølgen, og det er den der har været forkert hele tiden.
``jarvis_ui_guard`` normaliserer og degraderer på den fælles udgang — men den
kører EFTER svaret er formuleret, så dens eneste mulighed er at fjerne fladen
og efterlade en undskyldning. Brugeren ser resultatet af min fejl, og den
eneste vej tilbage er at han skriver igen.

Denne modul er den manglende runde: den tager den færdige tekst, spørger
guarden hvad der er galt (``fejl_i_flader``), og beder modellen rette KUN
fladerne — én gang, med et hårdt loft. Kan den ikke rettes, degraderes den
som før; korrektionen må aldrig gøre et svar værre end det var.

Designvalg der ikke er tilfældige:

* **Kun fladerne røres.** Prosaen er allerede formuleret og vist i streamen.
  En omskrivning af hele svaret ville koste et helt model-kald i tokens og
  kunne ændre indhold brugeren allerede har læst.
* **Én runde, ikke en løkke.** En korrektion der fejler, fejler. At prøve
  igen ville fordoble latency for et svar der sjældent bliver bedre af det.
* **Fail-open.** Kan modellen ikke kaldes, eller svarer den ubrugeligt,
  returneres den oprindelige tekst — guarden degraderer den derefter som i
  dag. Et svar må aldrig gå tabt på at forsøge at forbedre det.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

#: Loft for hvor mange tegn der sendes til korrektion. Et svar på 20.000 tegn
#: med én skæv blok skal ikke koste et helt nyt svar — vi sender kun det
#: nødvendige vindue omkring blokkene.
_MAX_KONTEKST = 6000

#: Hvor mange tegn prosa der tages med på hver side af en blok, så modellen
#: kan se hvad fladen skal indeholde.
_VINDUE = 400

_KORREKTIONS_INSTRUKS = """\
Dit svar er allerede skrevet og vist for brugeren. Én eller flere \
```jarvis-ui```-blokke i det kan ikke rendres, og brugeren ser derfor en \
tom eller degraderet flade i stedet for den du skrev.

Ret KUN de defekte blokke. Regler:

1. Returnér HELE svaret igen, ordret som det var — inklusive al prosa, alle \
overskrifter og alle andre blokke. Ændr ikke ét ord uden for de defekte blokke.
2. Ret kun det der er galt i JSON'en: manglende felter, forkerte længder, \
ugyldig syntaks. Behold indholdet — samme titel, samme rækker, samme tekst.
3. Blokken skal stå som ```jarvis-ui på sin egen linje, JSON på de følgende \
linjer, og ``` på sin egen linje til sidst.
4. Kan en blok ikke reddes uden at opfinde data, fjern blokken helt og lad \
prosaen stå. Opfind aldrig et tal, en titel eller en række der ikke var der.
5. Skriv ingen forklaring, ingen indledning, ingen afslutning. Kun svaret.
"""


def _blok_vinduer(tekst: str) -> str:
    """Uddrag af teksten omkring hver ``jarvis-ui``-blok.

    Et langt svar med én skæv blok skal ikke sendes i sin helhed: det koster
    tokens og giver modellen mere at ødelægge. Vinduet viser nok prosa til at
    den kan se hvad fladen skal bære.
    """
    if len(tekst) <= _MAX_KONTEKST:
        return tekst
    dele: list[str] = []
    for match in re.finditer(r"```jarvis-ui.*?```", tekst, re.S):
        start = max(0, match.start() - _VINDUE)
        slut = min(len(tekst), match.end() + _VINDUE)
        dele.append(tekst[start:slut])
    if not dele:
        return tekst[:_MAX_KONTEKST]
    return "\n\n[…]\n\n".join(dele)[:_MAX_KONTEKST]


def korriger_flader(
    tekst: str,
    fejl: list[str],
    *,
    stream_followup,
    provider: str,
    model: str,
    base_messages: list[dict],
    run_id: str = "",
    session_id: str = "",
) -> str:
    """Bed modellen rette defekte ``jarvis-ui``-blokke. Returnerer ny tekst.

    ``stream_followup`` er ``stream_visible_followup`` (injektionspunktet der
    gør funktionen testbar uden netværk). Returnerer den OPRINDELIGE tekst ved
    enhver fejl — en korrektion der ikke kan gennemføres må ikke koste svaret.
    """
    if not tekst or not fejl:
        return tekst
    try:
        from core.services.visible_followup_events import (
            FollowupDelta,
            FollowupDone,
            FollowupFailed,
        )
    except Exception:
        logger.debug("flade_korrektion: kunne ikke importere events", exc_info=True)
        return tekst

    uddrag = _blok_vinduer(tekst)
    opgave = (
        "Fejlene der gør blokkene ubrugelige:\n"
        + "\n".join(f"- {f}" for f in fejl[:6])
        + "\n\nSvaret der skal rettes:\n\n"
        + uddrag
    )
    trailing = [
        {"role": "user", "content": _KORREKTIONS_INSTRUKS + "\n\n" + opgave},
    ]

    dele: list[str] = []
    try:
        for event in stream_followup(
            provider=provider,
            model=model,
            base_messages=base_messages,
            exchanges=[],
            tool_definitions=None,
            round_index=0,
            thinking_mode="fast",
            run_id=run_id,
            session_id=session_id,
            trailing_messages=trailing,
        ):
            if isinstance(event, FollowupDelta):
                dele.append(event.delta)
            elif isinstance(event, FollowupDone):
                if event.text and not dele:
                    dele.append(event.text)
                break
            elif isinstance(event, FollowupFailed):
                logger.debug("flade_korrektion: runden fejlede: %s", event.error)
                return tekst
    except Exception:
        logger.debug("flade_korrektion: kaldet fejlede", exc_info=True)
        return tekst

    nyt = "".join(dele).strip()
    if not nyt:
        return tekst

    # Modellen fik hele svaret med i opgaven. Svarer den kun med blokkene,
    # er det stadig brugbart hvis det indeholder en flade — men et svar der
    # har mistet sin prosa må ikke erstatte det oprindelige.
    if "```jarvis-ui" not in nyt:
        return tekst
    if len(nyt) < len(tekst) * 0.5:
        logger.debug(
            "flade_korrektion: svaret var for kort (%d mod %d tegn) — forkastet",
            len(nyt), len(tekst),
        )
        return tekst

    # Kontrollér at korrektionen faktisk hjalp. Ellers er den bare en anden fejl.
    try:
        from core.services.jarvis_ui_guard import fejl_i_flader as _fejl_efter
    except Exception:  # import kan fejle i en delt proces; uden kontrollen er korrektionen stadig brugbar
        return nyt
    if _fejl_efter(nyt):
        logger.debug("flade_korrektion: korrektionen havde stadig fejl — forkastet")
        return tekst
    return nyt
